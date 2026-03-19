from app.components.langcache.embedding import cosine_similarity, embed_text


def test_embedding_is_stable_for_similar_support_questions():
    password_reset = embed_text("How do I reset my password?")
    password_change = embed_text("How do I change my login password?")

    assert password_reset == embed_text("How do I reset my password?")
    assert cosine_similarity(password_reset, password_change) > 0.6


def test_embedding_is_lower_for_unrelated_questions():
    password_reset = embed_text("How do I reset my password?")
    shipping_update = embed_text("Where is my package?")

    assert cosine_similarity(password_reset, shipping_update) < 0.6

