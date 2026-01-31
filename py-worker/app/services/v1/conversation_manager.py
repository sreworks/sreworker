"""对话管理服务 - 独立的 conversation 管理逻辑"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import os
from pathlib import Path
import uuid
import shutil
from ...utils.logger import get_app_logger


class ConversationModel:
    """对话数据模型"""

    def __init__(
        self,
        id: str,
        name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.name = name or f"Conversation {id[:8]}"
        self.created_at = created_at or datetime.utcnow()
        self.last_activity = last_activity or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata
        }


class BaseConversationManager(ABC):
    """对话管理器抽象接口"""

    @abstractmethod
    async def new_conversation(self, name: Optional[str] = None) -> str:
        """创建新对话"""
        pass

    @abstractmethod
    async def clone_conversation(self, conversation_id: str, new_name: Optional[str] = None) -> str:
        """克隆对话"""
        pass

    @abstractmethod
    async def list_conversations(self) -> List[ConversationModel]:
        """列出所有对话"""
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """获取指定对话"""
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        pass

    @abstractmethod
    async def switch_conversation(self, conversation_id: str) -> bool:
        """切换到指定对话"""
        pass

    @abstractmethod
    def get_current_conversation(self) -> Optional[str]:
        """获取当前对话 ID"""
        pass

    @abstractmethod
    async def rename_conversation(self, conversation_id: str, new_name: str) -> bool:
        """重命名对话"""
        pass

    @abstractmethod
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的消息历史"""
        pass


class ClaudeConversationManager(BaseConversationManager):
    """Claude Code 的对话管理器实现"""

    def __init__(self, project_path: str, worker_id: str):
        """
        初始化 Claude 对话管理器

        Args:
            project_path: 项目路径
            worker_id: worker ID（用于隔离）
        """
        self.project_path = project_path
        self.worker_id = worker_id
        self.claude_dir = Path(project_path) / ".claude"
        self.sessions_dir = self.claude_dir / "sessions"
        self.current_conversation_id: Optional[str] = None
        self.conversations_cache: Dict[str, ConversationModel] = {}
        self.logger = get_app_logger()

        # 确保目录存在
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    async def new_conversation(self, name: Optional[str] = None) -> str:
        """
        创建新对话

        实现方式：
        1. 生成新的 conversation ID
        2. 在 sessions 目录创建新的对话文件夹
        3. 初始化对话元数据
        4. 切换到新对话
        """
        conversation_id = str(uuid.uuid4())

        # 创建对话目录
        conv_dir = self.sessions_dir / conversation_id
        conv_dir.mkdir(exist_ok=True)

        # 创建对话模型
        conversation = ConversationModel(
            id=conversation_id,
            name=name or f"Conversation {conversation_id[:8]}"
        )

        # 保存元数据
        metadata_file = conv_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(conversation.to_dict(), f, indent=2)

        # 缓存
        self.conversations_cache[conversation_id] = conversation

        # 切换到新对话
        await self.switch_conversation(conversation_id)

        self.logger.info(f"Created new conversation: {conversation_id} ({conversation.name})")

        return conversation_id

    async def clone_conversation(self, conversation_id: str, new_name: Optional[str] = None) -> str:
        """
        克隆对话

        实现方式：
        1. 读取原对话的所有数据
        2. 创建新的对话 ID
        3. 复制对话数据到新目录
        4. 更新元数据
        """
        # 检查原对话是否存在
        source_dir = self.sessions_dir / conversation_id
        if not source_dir.exists():
            raise ValueError(f"Conversation not found: {conversation_id}")

        # 创建新对话 ID
        new_id = str(uuid.uuid4())
        target_dir = self.sessions_dir / new_id

        # 复制整个对话目录
        shutil.copytree(source_dir, target_dir)

        # 更新元数据
        metadata_file = target_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        metadata['id'] = new_id
        metadata['name'] = new_name or f"{metadata.get('name', 'Conversation')} (Copy)"
        metadata['created_at'] = datetime.utcnow().isoformat()
        metadata['cloned_from'] = conversation_id

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # 创建对话模型并缓存
        conversation = ConversationModel(
            id=new_id,
            name=metadata['name'],
            created_at=datetime.fromisoformat(metadata['created_at']),
            metadata=metadata.get('metadata', {})
        )
        self.conversations_cache[new_id] = conversation

        self.logger.info(f"Cloned conversation {conversation_id} to {new_id}")

        return new_id

    async def list_conversations(self) -> List[ConversationModel]:
        """列出所有对话"""
        conversations = []

        if not self.sessions_dir.exists():
            return conversations

        for conv_dir in self.sessions_dir.iterdir():
            if not conv_dir.is_dir():
                continue

            conversation_id = conv_dir.name

            # 从缓存获取
            if conversation_id in self.conversations_cache:
                conversations.append(self.conversations_cache[conversation_id])
                continue

            # 读取元数据
            metadata_file = conv_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        data = json.load(f)

                    conversation = ConversationModel(
                        id=data.get('id', conversation_id),
                        name=data.get('name'),
                        created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
                        last_activity=datetime.fromisoformat(data['last_activity']) if 'last_activity' in data else None,
                        metadata=data.get('metadata', {})
                    )
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Failed to parse conversation metadata for {conversation_id}: {e}")
                    conversation = ConversationModel(id=conversation_id)
            else:
                # 如果没有元数据，创建基本的对话模型
                conversation = ConversationModel(id=conversation_id)

            self.conversations_cache[conversation_id] = conversation
            conversations.append(conversation)

        # 按最后活动时间排序
        conversations.sort(key=lambda c: c.last_activity, reverse=True)
        return conversations

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """获取指定对话"""
        # 先从缓存获取
        if conversation_id in self.conversations_cache:
            return self.conversations_cache[conversation_id]

        # 从文件系统读取
        conv_dir = self.sessions_dir / conversation_id
        if not conv_dir.exists():
            return None

        metadata_file = conv_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)

                conversation = ConversationModel(
                    id=data.get('id', conversation_id),
                    name=data.get('name'),
                    created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
                    last_activity=datetime.fromisoformat(data['last_activity']) if 'last_activity' in data else None,
                    metadata=data.get('metadata', {})
                )
                self.conversations_cache[conversation_id] = conversation
                return conversation
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Failed to parse conversation metadata: {e}")

        return None

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        conv_dir = self.sessions_dir / conversation_id
        if not conv_dir.exists():
            return False

        # 不能删除当前对话
        if conversation_id == self.current_conversation_id:
            raise ValueError("Cannot delete current conversation. Switch to another conversation first.")

        # 删除目录
        shutil.rmtree(conv_dir)

        # 从缓存移除
        if conversation_id in self.conversations_cache:
            del self.conversations_cache[conversation_id]

        self.logger.info(f"Deleted conversation: {conversation_id}")

        return True

    async def switch_conversation(self, conversation_id: str) -> bool:
        """切换到指定对话"""
        conv_dir = self.sessions_dir / conversation_id
        if not conv_dir.exists():
            raise ValueError(f"Conversation not found: {conversation_id}")

        self.current_conversation_id = conversation_id

        # 更新最后活动时间
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            conversation.last_activity = datetime.utcnow()
            await self._save_conversation_metadata(conversation)

        self.logger.info(f"Switched to conversation: {conversation_id}")

        return True

    def get_current_conversation(self) -> Optional[str]:
        """获取当前对话 ID"""
        return self.current_conversation_id

    async def rename_conversation(self, conversation_id: str, new_name: str) -> bool:
        """重命名对话"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.name = new_name
        await self._save_conversation_metadata(conversation)

        self.logger.info(f"Renamed conversation {conversation_id} to '{new_name}'")

        return True

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的消息历史"""
        conv_dir = self.sessions_dir / conversation_id
        messages_file = conv_dir / "messages.jsonl"

        if not messages_file.exists():
            return []

        messages = []
        with open(messages_file, 'r') as f:
            for line in f:
                try:
                    message = json.loads(line.strip())
                    messages.append(message)
                except json.JSONDecodeError:
                    continue

        return messages

    async def _save_conversation_metadata(self, conversation: ConversationModel):
        """保存对话元数据"""
        conv_dir = self.sessions_dir / conversation.id
        metadata_file = conv_dir / "metadata.json"

        with open(metadata_file, 'w') as f:
            json.dump(conversation.to_dict(), f, indent=2)


class OpenCodeConversationManager(BaseConversationManager):
    """OpenCode 的对话管理器实现"""

    def __init__(self, project_path: str, worker_id: str):
        self.project_path = project_path
        self.worker_id = worker_id
        # OpenCode 可能有不同的存储方式
        self.config_dir = Path(project_path) / ".opencode"
        self.current_conversation_id: Optional[str] = None
        self.conversations_cache: Dict[str, ConversationModel] = {}
        self.logger = get_app_logger()

        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

    async def new_conversation(self, name: Optional[str] = None) -> str:
        """OpenCode 特定实现 - 目前简化实现"""
        conversation_id = str(uuid.uuid4())

        conversation = ConversationModel(
            id=conversation_id,
            name=name or f"Conversation {conversation_id[:8]}"
        )

        self.conversations_cache[conversation_id] = conversation
        self.current_conversation_id = conversation_id

        self.logger.info(f"Created new OpenCode conversation: {conversation_id}")

        return conversation_id

    async def clone_conversation(self, conversation_id: str, new_name: Optional[str] = None) -> str:
        """克隆对话 - 简化实现"""
        if conversation_id not in self.conversations_cache:
            raise ValueError(f"Conversation not found: {conversation_id}")

        new_id = str(uuid.uuid4())
        original = self.conversations_cache[conversation_id]

        cloned = ConversationModel(
            id=new_id,
            name=new_name or f"{original.name} (Copy)"
        )

        self.conversations_cache[new_id] = cloned

        self.logger.info(f"Cloned OpenCode conversation {conversation_id} to {new_id}")

        return new_id

    async def list_conversations(self) -> List[ConversationModel]:
        """列出所有对话"""
        conversations = list(self.conversations_cache.values())
        conversations.sort(key=lambda c: c.last_activity, reverse=True)
        return conversations

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """获取指定对话"""
        return self.conversations_cache.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id not in self.conversations_cache:
            return False

        if conversation_id == self.current_conversation_id:
            raise ValueError("Cannot delete current conversation. Switch to another conversation first.")

        del self.conversations_cache[conversation_id]

        self.logger.info(f"Deleted OpenCode conversation: {conversation_id}")

        return True

    async def switch_conversation(self, conversation_id: str) -> bool:
        """切换到指定对话"""
        if conversation_id not in self.conversations_cache:
            raise ValueError(f"Conversation not found: {conversation_id}")

        self.current_conversation_id = conversation_id

        conversation = self.conversations_cache[conversation_id]
        conversation.last_activity = datetime.utcnow()

        self.logger.info(f"Switched to OpenCode conversation: {conversation_id}")

        return True

    def get_current_conversation(self) -> Optional[str]:
        """获取当前对话 ID"""
        return self.current_conversation_id

    async def rename_conversation(self, conversation_id: str, new_name: str) -> bool:
        """重命名对话"""
        conversation = self.conversations_cache.get(conversation_id)
        if not conversation:
            return False

        conversation.name = new_name

        self.logger.info(f"Renamed OpenCode conversation {conversation_id} to '{new_name}'")

        return True

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的消息历史 - 简化实现"""
        # OpenCode 的消息历史可能需要从其他地方获取
        return []
