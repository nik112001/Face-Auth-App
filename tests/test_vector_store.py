import numpy as np

from vector_store import LocalStore, cosine_similarity


def _random_unit_vector(seed, dim=512):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=dim)
    return v / np.linalg.norm(v)


def test_cosine_similarity_of_vector_with_itself_is_one():
    v = _random_unit_vector(seed=1)
    assert np.isclose(cosine_similarity(v, v), 1.0, atol=1e-6)


def test_verify_matches_same_vector_and_rejects_different_one():
    store = LocalStore(path="test_vectors.json")
    enrolled = _random_unit_vector(seed=2)
    other = _random_unit_vector(seed=3)

    store.enroll("alice", enrolled)

    same_score = store.verify("alice", enrolled)
    different_score = store.verify("alice", other)

    assert same_score >= 0.5
    assert different_score < 0.5


def test_identify_returns_enrolled_user_for_their_own_vector():
    store = LocalStore(path="test_vectors_identify.json")
    alice_vec = _random_unit_vector(seed=4)
    bob_vec = _random_unit_vector(seed=5)

    store.enroll("alice", alice_vec)
    store.enroll("bob", bob_vec)

    user_id, score = store.identify(alice_vec)

    assert user_id == "alice"
    assert score >= 0.5
