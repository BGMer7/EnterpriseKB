"""
Embedding模型管理
支持BGE-M3等中文embedding模型
支持多模态embedding（图像+文本）
支持云端Embedding（OpenAI、Cohere等）
"""
from typing import List, Union, Optional
import torch

from app.config import settings

# 优先使用sentence-transformers（更稳定）
# 如果需要使用FlagEmbedding的特殊功能，可以切换
SENTENCE_TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None

# 尝试导入FlagEmbedding（可选，用于高级功能）
FLAG_EMBEDDING_AVAILABLE = False
try:
    from FlagEmbedding import BGEM3FlagModel
    FLAG_EMBEDDING_AVAILABLE = True
except ImportError:
    BGEM3FlagModel = None

# 可选的图像embedding支持
try:
    from PIL import Image
    import numpy as np

    # 尝试加载CLIP模型用于图像embedding
    CLIP_AVAILABLE = True
    try:
        from transformers import CLIPProcessor, CLIPModel
    except ImportError:
        CLIP_AVAILABLE = False
        CLIPModel = None
        CLIPProcessor = None
except ImportError:
    CLIP_AVAILABLE = False
    CLIPModel = None
    CLIPProcessor = None


class EmbeddingModel:
    """
    Embedding模型基类
    """

    def __init__(self, model_name: str, device: str = None):
        self.model_name = model_name
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._dimension = None

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32
    ) -> torch.Tensor:
        """
        编码文本为向量

        Args:
            texts: 文本或文本列表
            batch_size: 批处理大小

        Returns:
            torch.Tensor: 向量或向量矩阵
        """
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            # 单次编码获取维度
            result = self.encode(["test"])
            self._dimension = result.shape[-1]
        return self._dimension

    def to(self, device: str):
        """移动模型到指定设备"""
        self.device = device
        if self._model:
            self._model.to(device)
        return self


class BGEModel(EmbeddingModel):
    """
    BGE系列Embedding模型
    支持BGE-M3等多语言模型
    使用sentence-transformers作为后端（更稳定）
    """

    def __init__(
        self,
        model_name: str = settings.EMBEDDING_MODEL,
        device: str = None,
        use_fp16: bool = True
    ):
        super().__init__(model_name, device)
        self.use_fp16 = use_fp16
        self._load_model()

    def _load_model(self):
        """加载模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

        # 检测可用设备
        import torch
        if self.device == "cuda" and not torch.cuda.is_available():
            print(f"[EMBEDDING] Warning: CUDA not available, using CPU instead")
            self.device = "cpu"

        # 使用sentence-transformers加载所有模型（包括BGE-M3）
        # BGE-M3在sentence-transformers中会自动使用正确的后端
        self._model = SentenceTransformer(
            self.model_name,
            device=self.device
        )

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32
    ) -> torch.Tensor:
        """
        编码文本为向量

        Args:
            texts: 文本或文本列表
            batch_size: 批处理大小

        Returns:
            torch.Tensor: 向量或向量矩阵
        """
        if isinstance(texts, str):
            texts = [texts]

        # sentence-transformers统一接口
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return torch.tensor(embeddings)

    def encode_queries(
        self,
        queries: Union[str, List[str]],
        batch_size: int = 32
    ) -> torch.Tensor:
        """
        编码查询（查询和文档使用相同的encode方法）
        """
        if isinstance(queries, str):
            queries = [queries]

        # sentence-transformers统一处理
        embeddings = self._model.encode(
            queries,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return torch.tensor(embeddings)

    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._dimension is None:
            # 通过单次编码获取维度
            result = self.encode(["test"])
            self._dimension = result.shape[-1]
        return self._dimension


# 全局Embedding模型实例
_embedding_model: EmbeddingModel = None


def get_embedding_model() -> EmbeddingModel:
    """
    获取Embedding模型单例

    Returns:
        EmbeddingModel: Embedding模型实例
    """
    global _embedding_model

    if _embedding_model is None:
        import time
        t0 = time.time()
        print(f"[EMBEDDING] Loading model: {settings.EMBEDDING_MODEL}")
        _embedding_model = BGEModel(
            model_name=settings.EMBEDDING_MODEL,
            device=settings.EMBEDDING_DEVICE
        )
        t1 = time.time()
        print(f"[EMBEDDING] Model loaded in {t1-t0:.2f}s")
    else:
        print(f"[EMBEDDING] Using cached model (id: {id(_embedding_model)})")

    return _embedding_model


def encode_text(text: Union[str, List[str]]) -> List[List[float]]:
    """
    编码文本为向量（便捷函数）

    Args:
        text: 文本或文本列表

    Returns:
        List[List[float]]: 向量列表
    """
    model = get_embedding_model()
    embeddings = model.encode(text)
    return embeddings.tolist()


def encode_query(query: str) -> List[float]:
    """
    编码查询为向量（便捷函数）

    Args:
        query: 查询文本

    Returns:
        List[float]: 向量
    """
    model = get_embedding_model()
    embedding = model.encode_queries(query)
    return embedding.squeeze().tolist()


# 多模态Embedding模型
_clip_model = None
_clip_processor = None


class MultimodalEmbeddingModel:
    """
    多模态Embedding模型
    支持图像和文本的联合向量化
    """

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: str = None
    ):
        self.model_name = model_name
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._processor = None

    def _load_model(self):
        """加载CLIP模型"""
        global _clip_model, _clip_processor

        if not CLIP_AVAILABLE:
            raise ImportError("CLIP dependencies not available. Install: pip install transformers pillow numpy")

        if _clip_model is None:
            try:
                _clip_processor = CLIPProcessor.from_pretrained(self.model_name)
                _clip_model = CLIPModel.from_pretrained(self.model_name)
                _clip_model.to(self.device)
                _clip_model.eval()
            except Exception as e:
                raise RuntimeError(f"Failed to load CLIP model: {e}")

        self._model = _clip_model
        self._processor = _clip_processor

    def encode_image(self, image_path: str) -> List[float]:
        """
        编码图像为向量

        Args:
            image_path: 图像路径

        Returns:
            List[float]: 图像向量
        """
        if self._model is None:
            self._load_model()

        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self._model.get_image_features(**inputs)

            return image_features.squeeze().cpu().tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to encode image: {e}")

    def encode_image_bytes(self, image_bytes: bytes) -> List[float]:
        """
        编码图像字节为向量

        Args:
            image_bytes: 图像字节数据

        Returns:
            List[float]: 图像向量
        """
        if self._model is None:
            self._load_model()

        try:
            image = Image.open(image_bytes).convert("RGB")
            inputs = self._processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self._model.get_image_features(**inputs)

            return image_features.squeeze().cpu().tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to encode image bytes: {e}")

    def encode_text(self, text: str) -> List[float]:
        """
        编码文本为向量

        Args:
            text: 文本

        Returns:
            List[float]: 文本向量
        """
        if self._model is None:
            self._load_model()

        try:
            inputs = self._processor(text=text, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                text_features = self._model.get_text_features(**inputs)

            return text_features.squeeze().cpu().tolist()
        except Exception as e:
            raise RuntimeError(f"Failed to encode text: {e}")

    def encode_multimodal(
        self,
        text: str,
        image_paths: List[str] = None
    ) -> List[float]:
        """
        编码多模态内容（文本+图像）

        Args:
            text: 文本内容
            image_paths: 图像路径列表

        Returns:
            List[float]: 多模态向量
        """
        # 简单实现：先获取文本向量，如果有图像则平均
        text_embedding = self.encode_text(text)

        if image_paths:
            image_embeddings = []
            for img_path in image_paths:
                try:
                    img_emb = self.encode_image(img_path)
                    image_embeddings.append(img_emb)
                except Exception:
                    pass

            if image_embeddings:
                # 平均文本和图像向量
                import numpy as np
                text_arr = np.array(text_embedding)
                img_arr = np.mean(image_embeddings, axis=0)
                # 加权组合（文本权重更高）
                multimodal = 0.7 * text_arr + 0.3 * img_arr
                return multimodal.tolist()

        return text_embedding


# 全局多模态embedding模型实例
_multimodal_embedding_model: Optional[MultimodalEmbeddingModel] = None


def get_multimodal_embedding_model() -> MultimodalEmbeddingModel:
    """
    获取多模态Embedding模型单例

    Returns:
        MultimodalEmbeddingModel: 多模态embedding模型实例
    """
    global _multimodal_embedding_model

    if _multimodal_embedding_model is None:
        try:
            _multimodal_embedding_model = MultimodalEmbeddingModel(
                model_name="openai/clip-vit-base-patch32",
                device=settings.EMBEDDING_DEVICE
            )
        except ImportError as e:
            raise ImportError(f"Multimodal embedding not available: {e}")

    return _multimodal_embedding_model


def is_multimodal_embedding_available() -> bool:
    """
    检查多模态embedding是否可用

    Returns:
        bool: 是否可用
    """
    return CLIP_AVAILABLE
