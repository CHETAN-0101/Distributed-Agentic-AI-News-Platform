"""Unit tests for AgentOS Pydantic data schemas."""
import pytest
from datetime import datetime, timezone
from shared.schemas import (
    AgentCapability,
    AgentRegistration,
    AgentHealthReport,
    TaskInput,
    TaskOutput,
    TaskStatus,
    TaskPriority,
    WorkflowNode,
    WorkflowGraph,
    WorkflowStatus,
    WorkflowCreate,
    EvidenceItem,
    EvidenceType,
    Claim,
    ClaimStatus,
    NewsArticle,
    NewsEvent,
    NewsVerificationState,
    MemoryEntry,
    MemoryType,
    ApprovalRequest,
    RiskLevel,
)


def test_agent_registration_schema():
    cap = AgentCapability(
        name="web_search",
        version="1.0.0",
        description="Search public web sources",
    )
    reg = AgentRegistration(
        agent_id="research-agent-01",
        name="Research Agent",
        version="1.0.0",
        host="localhost",
        port=8001,
        capabilities=["web_search"],
        capability_details=[cap],
    )
    assert reg.agent_id == "research-agent-01"
    assert len(reg.capabilities) == 1
    assert reg.capabilities[0] == "web_search"
    assert reg.host == "localhost"
    assert reg.port == 8001


def test_task_lifecycle_schemas():
    task_in = TaskInput(
        task_id="task-101",
        workflow_id="wf-202",
        agent_id="research-agent-01",
        capability="web_search",
        input={"query": "AI agents in 2026"},
        priority=TaskPriority.HIGH,
    )
    assert task_in.task_id == "task-101"
    assert task_in.capability == "web_search"
    assert task_in.priority == TaskPriority.HIGH

    task_out = TaskOutput(
        task_id="task-101",
        agent_id="research-agent-01",
        status=TaskStatus.COMPLETED,
        result={"summary": "AgentOS is a distributed platform"},
        confidence=0.95,
    )
    assert task_out.status == TaskStatus.COMPLETED
    assert task_out.confidence == 0.95


def test_evidence_and_claims():
    evidence = EvidenceItem(
        evidence_id="ev-101",
        source_url="https://example.com/news/1",
        source_name="OpenAI Announcements",
        credibility=0.92,
        content="GPT-5 released today.",
        evidence_type=EvidenceType.SUPPORTED_FACT,
    )
    assert evidence.credibility == 0.92
    assert evidence.evidence_type == EvidenceType.SUPPORTED_FACT

    claim = Claim(
        claim_id="claim-01",
        text="GPT-5 has been officially unveiled",
        status=ClaimStatus.CONFIRMED,
        confidence=0.95,
        evidence_ids=["ev-101"],
        evidence=[evidence],
    )
    assert claim.status == ClaimStatus.CONFIRMED
    assert len(claim.evidence_ids) == 1


def test_news_article_and_event():
    article = NewsArticle(
        article_id="art-001",
        title="Google DeepMind Advances Frontier AI Safety",
        url="https://deepmind.google/news/safety",
        source="DeepMind Blog",
        content="Research on multi-agent alignment...",
        published_at=datetime.now(timezone.utc),
    )
    assert article.source == "DeepMind Blog"
    assert article.content == "Research on multi-agent alignment..."

    event = NewsEvent(
        event_id="evt-001",
        title="AI Safety Breakthrough",
        description="DeepMind introduces multi-agent verification guarantees.",
        article_ids=[article.article_id],
    )
    assert event.title == "AI Safety Breakthrough"
    assert len(event.article_ids) == 1


def test_approval_request_schema():
    req = ApprovalRequest(
        approval_id="appr-001",
        workflow_id="wf-500",
        task_id="task-800",
        requested_by="finance-agent",
        action="execute_external_trade",
        proposed_change={"amount": 50000, "asset": "ETH"},
        risk_level=RiskLevel.HIGH,
        reason="Exceeds automated threshold of $10,000",
    )
    assert req.risk_level == RiskLevel.HIGH
    assert req.requested_by == "finance-agent"
    assert req.proposed_change["amount"] == 50000
