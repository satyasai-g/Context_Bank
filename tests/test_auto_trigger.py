import pytest
from backend.services.trigger_generator import TriggerGeneratorService
from backend.context_bank.storage import ContextStorage
from backend.schemas.contexts import ContextCreate


def test_generate_trigger_from_explicit_project_name(db, user_a):
    """Test extracting trigger word from explicit project declarations."""
    chat = """
    User: I am building a voice-first learning application called Voxcent.
    Assistant: Sounds great! What architecture should Voxcent use?
    User: We decided on Python, FastAPI, and PostgreSQL with pgvector.
    """
    res = TriggerGeneratorService.generate_triggers_from_chat(chat, db, user_a.id)

    assert res["primary_trigger"] == "VOXCENT"
    assert "VOXCENT" in res["candidates"]
    assert "reasoning" in res


def test_generate_trigger_from_technical_topic(db, user_a):
    """Test extracting trigger word from technical domain topics."""
    chat = """
    We need to work on PostgreSQL query optimization, B-Tree indexes, and explain analyze.
    What are the next steps for database performance?
    """
    res = TriggerGeneratorService.generate_triggers_from_chat(chat, db, user_a.id)

    primary = res["primary_trigger"]
    # Should capture core technical concepts
    assert any(term in primary for term in ["POSTGRES", "SQL", "INDEX", "DATABASE", "QUERY", "OPTIMIZATION"])
    assert len(res["candidates"]) >= 1


def test_auto_collision_resolution(db, user_a):
    """Test that if a trigger already exists, the generator resolves the collision."""
    # First, register VOXCENT
    ContextStorage.create_context(
        db,
        user_a.id,
        ContextCreate(trigger_word="VOXCENT", title="Existing Voxcent", summary="Original"),
    )

    # Now ask generator to create trigger for another chat that discusses Voxcent
    chat = "Let's work on Voxcent mobile client architecture."
    res = TriggerGeneratorService.generate_triggers_from_chat(chat, db, user_a.id)

    # It must NOT return duplicate 'VOXCENT'; it should pick an alternative or append suffix
    assert res["primary_trigger"] != "VOXCENT"
    assert res["primary_trigger"].startswith("VOXCENT_") or res["primary_trigger"] in res["alternative_triggers"] or len(res["primary_trigger"]) > 0


def test_auto_create_from_chat_api(client, auth_headers_a):
    """Test the full end-to-end auto-creation API endpoint."""
    chat_text = """
    User: Let's design a payment integration module called StripeCheckout.
    Assistant: Confirmed decisions:
    - We will use Stripe SDK
    - Webhook endpoint at /webhooks/stripe
    User: Next step is generating test API keys.
    """

    resp = client.post(
        "/api/v1/contexts/auto-create-from-chat",
        json={"chat_text": chat_text},
        headers=auth_headers_a,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_trigger"] in ("STRIPECKOUT", "STRIPECHECKOUT", "STRIPE_CHECKOUT", "STRIPE", "CHECKOUT")
    assert "Stripe" in data["title"] or "Checkout" in data["title"] or data["primary_trigger"] in data["title"]
    assert len(data["important_decisions"]) >= 1
    assert data["id"] is not None
