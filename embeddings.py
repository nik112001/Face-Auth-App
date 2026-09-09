"""Face embedding extraction.

Model choice: facenet-pytorch (MTCNN for detection/alignment, InceptionResnetV1
pretrained on VGGFace2 for the 512-d embedding). Chosen over insightface/ArcFace
because it is pure PyTorch (no ONNXRuntime dependency), which keeps the whole
stack in one framework.
"""

import numpy as np
from PIL import Image

_mtcnn = None
_resnet = None


def _get_models():
    global _mtcnn, _resnet
    if _mtcnn is None or _resnet is None:
        # Imported lazily so importing this module doesn't pull in torch
        # until a face actually needs to be embedded.
        import torch
        from facenet_pytorch import MTCNN, InceptionResnetV1

        _mtcnn = MTCNN(image_size=160, margin=0, keep_all=False)
        _resnet = InceptionResnetV1(pretrained="vggface2").eval()
    return _mtcnn, _resnet


def embed_face(bgr_image: np.ndarray):
    """Detect the largest single face in a BGR image and return its
    L2-normalized 512-d embedding, or None if zero or more than one
    face is detected (reject ambiguous frames, same rule as v1)."""
    import torch

    mtcnn, resnet = _get_models()

    rgb_image = bgr_image[:, :, ::-1]
    pil_image = Image.fromarray(rgb_image)

    with torch.no_grad():
        boxes, _probs = mtcnn.detect(pil_image)
        if boxes is None or len(boxes) != 1:
            return None

        face_tensor = mtcnn(pil_image)
        if face_tensor is None:
            return None

        embedding = resnet(face_tensor.unsqueeze(0))[0].numpy()

    norm = np.linalg.norm(embedding)
    if norm == 0:
        return None
    return embedding / norm
