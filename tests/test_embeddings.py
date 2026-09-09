import os

import cv2
import numpy as np

from conftest import FIXTURES_DIR
from embeddings import embed_face


def _load(name):
    return cv2.imread(os.path.join(FIXTURES_DIR, name))


def test_no_face_returns_none():
    assert embed_face(_load("no_face.jpg")) is None


def test_multi_face_returns_none():
    assert embed_face(_load("two_faces.jpg")) is None


def test_single_face_returns_normalized_512d_vector():
    embedding = embed_face(_load("face1.jpg"))
    assert embedding is not None
    assert embedding.shape == (512,)
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-4)
