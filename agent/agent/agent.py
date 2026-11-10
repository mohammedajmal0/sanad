import os
from collections.abc import AsyncGenerator, Callable
from functools import lru_cache
from typing import Any

from databricks.sdk import WorkspaceClient
from databricks_agentkit import workspace_client, workspace_headers
from databricks_agentkit.langgraph import (
    checkpointer,
    configure_tracing,
    genie_tools,
    mcp_tools,
    memory_tools,
    start_trace,
    thread_config,
)
from databricks_agentkit.langgraph.messages import gateway_messages
from databricks_agentkit.langgraph.session_store import (
    invocation_id_from_metadata,
    invocation_metadata,
)
from databricks_agentkit.runtime.auth import AuthError
from databricks_agentkit.runtime.tool_manifest import resolve_model_service
from databricks_langchain import ChatDatabricks
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.middleware.human_in_the_loop import HITLResponse
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from pydantic import TypeAdapter, ValidationError

from agent.answer import StructuredAnswer
from agent.mcps import build_mcp_servers
from agent.prompt import SUPERVISOR, load_system_prompt

# Importing the tools package auto-registers every tool module.
from agent.tools import all_tools

# A Unity Catalog AI Gateway model service, served from the `system.ai` schema and queried through
# the gateway (see `use_ai_gateway=True` below). Swap for any `system.ai.*` model service your
# workspace exposes — the demo chat app's picker lists what's available.
# `agentbricks experimental models bind` swaps this for a model service you own (wired in by `agentbricks deploy`
# as AGENT_MODEL_SERVICE_AGENT), so `agentbricks experimental models upgrade` can change the model without a code
# change.
MODEL = (
    resolve_model_service() or "system.ai.gpt-oss-120b"
)  # Free Edition has no Claude (checked 2026-11-08)


def _approval_request(tool_call: Any, state: Any, runtime: Any) -> str:
    """What the approver reads before a write runs (written by Claude at my request)."""
    a, name = tool_call["args"], tool_call["name"]
    if name == "create_credit_note":
        return (
            f"Draft a credit note of SAR {a.get('amount_sar')} for {a.get('invoice_id')} "
            f"({a.get('reason_code')}: {a.get('reason')})? The ERP then holds it for the approver "
            "the Credit Note and Refund Policy requires."
        )
    if name == "create_ticket":
        return (
            f"Open a {a.get('priority', 'medium')} {a.get('category')} ticket: {a.get('summary')}"
        )
    if name == "create_case":
        return f"Open a CRM case for {a.get('account_id')}: {a.get('subject')}"
    if name == "post_teams_message":
        return f"Post to Teams #{a.get('channel')}: {a.get('text')}"
    return f"Run {name} with {a}?"  # a write tool added to the MCP server later


def approval_rules(tool_names: list[str]) -> dict:
    """Every Najm-system tool except a read (get_*) pauses for a person before it runs.

    Default deny: a tool the MCP server adds later is gated until someone decides otherwise. The
    agent emits an `interrupt`; the client resumes with `input.resume` and the same session id.
    "respond" is left out: the approver approves, edits the arguments, or rejects.
    """
    rule = {"allowed_decisions": ["approve", "edit", "reject"], "description": _approval_request}
    return {name: rule for name in tool_names if not name.startswith("get_")}


# The specialists the supervisor calls as tools (docs/adr/0005): the UC function tools each one
# gets (agent.toml ids; search_policies is shared) and the description the supervisor reads to
# route. Each has its prompt at sanad.prompts.<name>. Written by Claude at my request.
SPECIALISTS = {
    "customer_service": (
        {"get_customer_summary", "get_invoices", "get_invoice", "get_shipment_status",
         "search_policies"},
        (
            "Ask the Customer Service specialist about one customer's account, invoices, orders or "
            "shipments, or the billing, refund and delivery policies that apply to them. It looks the "
            "records up with the asking user's permissions and returns an Answer with citations. "
            "`question` must stand on its own: include the customer's name and any ids, dates or "
            "periods from the conversation."
        ),
    ),
    "service_desk": (
        {"get_ticket_trend", "search_policies"},
        (
            "Ask the Service Desk specialist about an IT problem a staff member reports (VPN, email, "
            "laptop, password, ERP access or printer). It checks whether recent tickets show an "
            "incident, finds the knowledge-base fix, and returns an Answer with citations. `question` "
            "must stand on its own: include the symptom and when it started."
        ),
    ),
}


class _RoutedChatDatabricks(ChatDatabricks):
    """Forward account-host workspace routing to the underlying OpenAI clients."""

    def _get_client_kwargs(self) -> dict[str, Any]:
        kwargs = super()._get_client_kwargs()
        if headers := workspace_headers():
            kwargs["default_headers"] = headers
        return kwargs

    def _prepare_inputs(self, messages: list[Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
        # Send Claude 5.x reasoning (and its signature) back to the model on the next turn.
        return super()._prepare_inputs(gateway_messages(messages), *args, **kwargs)


@lru_cache(maxsize=1)
def _app_workspace_client() -> WorkspaceClient:
    """The App's own client, shared across turns.

    Constructing a WorkspaceClient resolves auth with blocking network calls (and, locally, a
    `databricks auth token` subprocess). Doing that per turn inside the async graph builder stalls
    every request on the event loop; the SDK refreshes tokens itself, so one client suffices.
    """
    return workspace_client()


def configure() -> None:
    """Wire up global state; call once at server startup (not at import)."""
    _check_databricks_auth()
    configure_tracing()


def _check_databricks_auth() -> None:
    """Fail fast at startup with a clear message if Databricks auth isn't configured.

    Without this, a missing/invalid profile only surfaces on the first model call — as a generic SDK
    error buried in a request traceback. Resolving a WorkspaceClient here validates the same config
    the model client uses, so the failure is immediate and actionable.
    """
    try:
        _app_workspace_client()
    except Exception as e:
        profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        target = (
            f"profile {profile!r}" if profile else "the DEFAULT profile / DATABRICKS_HOST+TOKEN"
        )
        raise RuntimeError(
            f"Databricks auth is not configured — the agent can't call the model. Tried {target}.\n"
            "Fix one of:\n"
            "  • set DATABRICKS_CONFIG_PROFILE in .env to a profile from `databricks auth profiles`, or\n"
            "  • run `databricks auth login --profile <name>` to create one, or\n"
            "  • set DATABRICKS_HOST and DATABRICKS_TOKEN in .env.\n"
            f"(underlying error: {e})"
        ) from e


async def create_agent_graph(
    actor: str,
    model: str | None = None,
    *,
    workspace_client_for: Callable[[str], WorkspaceClient] | None = None,
):
    """Build the supervisor: it calls each specialist as a tool (docs/adr/0005).

    - Customer Service and Service Desk: each its own agent with its UC function tools (SPECIALISTS),
      wrapped as one tool.
    - Ops Analytics: the Genie agent bound in agent.toml (ops_analytics_ask, _poll, _query_result).
    - Local tools, memory tools and the approval gate stay on the supervisor.

    ``actor`` is the identity whose long-term memory the agent reads/writes; it's captured in the
    memory tools' closures (never exposed to the model).

    ``model`` selects the gateway model for this run; the chat UI passes the picker's choice and
    everything else falls back to ``MODEL``. The agent is rebuilt per turn, so the model can vary
    request to request.
    """
    mcp = await mcp_tools(build_mcp_servers(), workspace_client_for=workspace_client_for)
    endpoint = model or MODEL
    # use_ai_gateway routes to the Unity Catalog AI Gateway (`<host>/ai-gateway/mlflow/v1`), so
    # `endpoint` is a `system.ai.*` model name rather than a serving-endpoint name.
    llm = _RoutedChatDatabricks(
        endpoint=endpoint, workspace_client=_app_workspace_client(), use_ai_gateway=True
    )
    # UC function tools go to the specialists that own them; the rest of the MCP tools (Najm's
    # systems, from mcps.py) belong to the supervisor, which holds the approval gate.
    owned = set().union(*(ids for ids, _ in SPECIALISTS.values()))
    systems = [t for t in mcp if t.name.rsplit("__", 1)[-1] not in owned]
    tools = [
        *all_tools(),
        *systems,
        *memory_tools(actor),
        *genie_tools(workspace_client_for=workspace_client_for),
        *(_specialist(name, llm, mcp) for name in SPECIALISTS),
    ]
    gated = approval_rules([t.name for t in systems])
    middleware = [HumanInTheLoopMiddleware(interrupt_on=gated)] if gated else []
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=load_system_prompt(SUPERVISOR),  # MLflow Prompt Registry, @production
        # Every turn ends with a schema-checked Answer (agent/answer.py explains why not response_format).
        middleware=[*middleware, StructuredAnswer(llm)],
        checkpointer=checkpointer(),
    )


def _specialist(name: str, llm: Any, mcp: list[BaseTool]) -> BaseTool:
    """A specialist: its own agent, prompt and UC tools, wrapped as one supervisor tool."""
    tool_ids, description = SPECIALISTS[name]
    specialist = create_agent(
        model=llm,
        # MCP names UC function tools <catalog>__<schema>__<function>
        tools=[t for t in mcp if t.name.rsplit("__", 1)[-1] in tool_ids],
        system_prompt=load_system_prompt(name),
        middleware=[StructuredAnswer(llm)],
        # Stateless: each call starts fresh. None would inherit the supervisor's checkpointer and
        # store every inner step in the session; the supervisor holds the conversation.
        checkpointer=False,
    )

    async def ask(question: str) -> dict:
        # Workaround (LangGraph 1.2.20): a nested graph inherits run_agent's durability="sync",
        # and with checkpointer=False it then awaits a checkpoint save that never starts
        # (AttributeError: _put_checkpoint_fut). Passing the standalone default avoids that.
        result = await specialist.ainvoke(
            {"messages": [{"role": "user", "content": question}]}, durability="async"
        )
        return result["messages"][-1].additional_kwargs["answer"]

    return StructuredTool.from_function(coroutine=ask, name=name, description=description)


async def recovery_input(
    agent_input: Any,
    *,
    session_id: str,
    actor: str,
    invocation_id: str,
) -> Any:
    """Return the input that should be passed to ``run_agent`` after worker loss.

    A checkpoint tagged with this invocation means LangGraph can continue by receiving ``None``.
    Otherwise recovery replays the original application input.
    """
    checkpoint = await checkpointer().aget_tuple(thread_config(session_id, actor))
    current_invocation_checkpointed = bool(
        checkpoint and invocation_id_from_metadata(checkpoint.metadata) == invocation_id
    )
    return None if current_invocation_checkpointed else agent_input


async def _validate_approval_resume(graph: Any, config: dict, agent_input: Any) -> None:
    """Reject malformed middleware decisions before LangGraph checkpoints the resume value."""
    if not isinstance(agent_input, Command) or agent_input.resume is None:
        return
    state = await graph.aget_state(config)
    pending = [item for task in state.tasks for item in task.interrupts]
    resume = agent_input.resume
    keyed = isinstance(resume, dict) and any(item.id in resume for item in pending)
    for item in pending:
        if not isinstance(item.value, dict) or "review_configs" not in item.value:
            continue  # Application-defined interrupts keep their native resume contract.
        if keyed and item.id not in resume:
            continue
        response = resume[item.id] if keyed else resume
        try:
            decisions = TypeAdapter(HITLResponse).validate_python(response)["decisions"]
        except ValidationError as error:
            raise AuthError(
                "INVALID_APPROVAL", "Invalid approval decision payload.", 400
            ) from error
        reviews = item.value["review_configs"]
        if len(decisions) != len(reviews) or any(
            decision["type"] not in review["allowed_decisions"]
            for decision, review in zip(decisions, reviews, strict=True)
        ):
            raise AuthError(
                "INVALID_APPROVAL", "Provide one allowed decision per pending tool call.", 400
            )


async def run_agent(
    agent_input: Any,
    *,
    session_id: str,
    actor: str | None = None,
    model: str | None = None,
    invocation_id: str | None = None,
    workspace_client_for: Callable[[str], WorkspaceClient] | None = None,
    graph: Any = None,
) -> AsyncGenerator[Any, None]:
    """Run the agent and yield native LangGraph stream events.

    This is the framework-native entrypoint. It has no dependency on Agent Bricks request or context types,
    so it can be called from another server, a notebook, or a test harness.
    """
    # Each interactive resume builds tools from this request's credentials. Only graph state,
    # never the graph or its credential-bound clients, survives the approval pause.
    actor = actor or session_id
    if graph is None:
        graph = await create_agent_graph(actor, model, workspace_client_for=workspace_client_for)
    config = thread_config(session_id, actor)
    if invocation_id:
        config["metadata"] = invocation_metadata(invocation_id)

    await _validate_approval_resume(graph, config, agent_input)

    last_update: Any = None
    with start_trace(name="invoke", inputs=agent_input, session_id=session_id) as span:
        async for event in graph.astream(
            input=agent_input,
            config=config,
            stream_mode=["updates", "messages"],
            durability="sync",
        ):
            if event[0] == "updates":
                last_update = event[1]
            yield event
        if span is not None and last_update is not None:
            span.set_outputs(last_update)
