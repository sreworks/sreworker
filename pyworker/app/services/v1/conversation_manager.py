"""对话管理服务 - 独立的 conversation 管理逻辑"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
import json
import os
from pathlib import Path
import uuid
import shutil
from ...utils.logger import get_app_logger

if TYPE_CHECKING:
    from .database import DatabaseManager


class ConversationModel:
    """对话数据模型"""

    def __init__(
        self,
        id: str,
        project_path: str,
        name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_activity: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.project_path = project_path
        self.name = name or f"Conversation {id[:8]}"
        self.created_at = created_at or datetime.utcnow()
        self.last_activity = last_activity or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_path": self.project_path,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "metadata": self.metadata
        }


class BaseConversationManager(ABC):
    """对话管理器抽象接口"""

    @abstractmethod
    async def new_conversation(self, project_path: str, name: Optional[str] = None) -> str:
        """创建新对话"""
        pass

    @abstractmethod
    async def clone_conversation(self, conversation_id: str, new_name: Optional[str] = None) -> str:
        """克隆对话（继承原对话的 project_path）"""
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

    def __init__(self, worker_id: str, db: Optional['DatabaseManager'] = None):
        """
        初始化 Claude 对话管理器

        Args:
            worker_id: worker ID（用于隔离）
            db: 数据库管理器（可选）
        """
        self.worker_id = worker_id
        self.db = db
        self.current_conversation_id: Optional[str] = None
        self.conversations_cache: Dict[str, ConversationModel] = {}
        self.logger = get_app_logger()

        # 从数据库加载当前对话
        if self.db:
            self.current_conversation_id = self.db.get_current_conversation(worker_id)

    def _get_sessions_dir(self, project_path: str) -> Path:
        """获取指定项目的 sessions 目录"""
        sessions_dir = Path(project_path) / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

    async def new_conversation(self, project_path: str, name: Optional[str] = None) -> str:
        """
        创建新对话

        实现方式：
        1. 生成新的 conversation ID
        2. 在项目的 sessions 目录创建新的对话文件夹
        3. 初始化对话元数据
        4. 切换到新对话
        """
        conversation_id = str(uuid.uuid4())
        project_path = os.path.abspath(project_path)

        # 获取项目的 sessions 目录
        sessions_dir = self._get_sessions_dir(project_path)

        # 创建对话目录
        conv_dir = sessions_dir / conversation_id
        conv_dir.mkdir(exist_ok=True)

        # 创建对话模型
        conversation = ConversationModel(
            id=conversation_id,
            project_path=project_path,
            name=name or f"Conversation {conversation_id[:8]}"
        )

        # 保存元数据
        metadata_file = conv_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(conversation.to_dict(), f, indent=2)

        # 缓存
        self.conversations_cache[conversation_id] = conversation

        # 保存到数据库
        if self.db:
            self.db.create_conversation({
                'id': conversation_id,
                'worker_id': self.worker_id,
                'project_path': project_path,
                'name': conversation.name,
                'created_at': conversation.created_at,
                'last_activity': conversation.last_activity,
                'is_current': False,  # 切换时会设置为 True
                'metadata': conversation.metadata
            })

        # 切换到新对话
        await self.switch_conversation(conversation_id)

        self.logger.info(f"Created new conversation: {conversation_id} ({conversation.name}) at {project_path}")

        return conversation_id

    async def clone_conversation(self, conversation_id: str, new_name: Optional[str] = None) -> str:
        """
        克隆对话（继承原对话的 project_path）

        实现方式：
        1. 获取原对话的 project_path
        2. 读取原对话的所有数据
        3. 创建新的对话 ID
        4. 复制对话数据到新目录
        5. 更新元数据
        """
        # 获取原对话
        source_conv = await self.get_conversation(conversation_id)
        if not source_conv:
            raise ValueError(f"Conversation not found: {conversation_id}")

        project_path = source_conv.project_path
        sessions_dir = self._get_sessions_dir(project_path)

        # 检查原对话目录是否存在
        source_dir = sessions_dir / conversation_id
        if not source_dir.exists():
            raise ValueError(f"Conversation directory not found: {conversation_id}")

        # 创建新对话 ID
        new_id = str(uuid.uuid4())
        target_dir = sessions_dir / new_id

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
        metadata['project_path'] = project_path
        metadata['name'] = new_name or f"{metadata.get('name', 'Conversation')} (Copy)"
        metadata['created_at'] = datetime.utcnow().isoformat()
        metadata['cloned_from'] = conversation_id

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # 创建对话模型并缓存
        conversation = ConversationModel(
            id=new_id,
            project_path=project_path,
            name=metadata['name'],
            created_at=datetime.fromisoformat(metadata['created_at']),
            metadata=metadata.get('metadata', {})
        )
        self.conversations_cache[new_id] = conversation

        # 保存到数据库
        if self.db:
            self.db.create_conversation({
                'id': new_id,
                'worker_id': self.worker_id,
                'project_path': project_path,
                'name': conversation.name,
                'created_at': conversation.created_at,
                'last_activity': conversation.last_activity,
                'is_current': False,
                'metadata': {'cloned_from': conversation_id, **conversation.metadata}
            })

        self.logger.info(f"Cloned conversation {conversation_id} to {new_id}")

        return new_id

    async def list_conversations(self) -> List[ConversationModel]:
        """列出所有对话（从数据库或缓存）"""
        # 优先从数据库获取
        if self.db:
            db_conversations = self.db.list_conversations(self.worker_id)
            conversations = []
            for data in db_conversations:
                conversation = ConversationModel(
                    id=data['id'],
                    project_path=data.get('project_path', ''),
                    name=data.get('name'),
                    created_at=data.get('created_at'),
                    last_activity=data.get('last_activity'),
                    metadata=data.get('metadata', {})
                )
                self.conversations_cache[data['id']] = conversation
                conversations.append(conversation)
            return conversations

        # 如果没有数据库，返回缓存中的对话
        conversations = list(self.conversations_cache.values())
        conversations.sort(key=lambda c: c.last_activity, reverse=True)
        return conversations

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """获取指定对话"""
        # 先从缓存获取
        if conversation_id in self.conversations_cache:
            return self.conversations_cache[conversation_id]

        # 从数据库获取
        if self.db:
            data = self.db.get_conversation(conversation_id)
            if data:
                conversation = ConversationModel(
                    id=data['id'],
                    project_path=data.get('project_path', ''),
                    name=data.get('name'),
                    created_at=data.get('created_at'),
                    last_activity=data.get('last_activity'),
                    metadata=data.get('metadata', {})
                )
                self.conversations_cache[conversation_id] = conversation
                return conversation

        return None

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        # 获取对话以获取 project_path
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return False

        # 不能删除当前对话
        if conversation_id == self.current_conversation_id:
            raise ValueError("Cannot delete current conversation. Switch to another conversation first.")

        # 删除文件系统中的目录
        sessions_dir = self._get_sessions_dir(conversation.project_path)
        conv_dir = sessions_dir / conversation_id
        if conv_dir.exists():
            shutil.rmtree(conv_dir)

        # 从缓存移除
        if conversation_id in self.conversations_cache:
            del self.conversations_cache[conversation_id]

        # 从数据库删除
        if self.db:
            self.db.delete_conversation(conversation_id)

        self.logger.info(f"Deleted conversation: {conversation_id}")

        return True

    async def switch_conversation(self, conversation_id: str) -> bool:
        """切换到指定对话"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation not found: {conversation_id}")

        self.current_conversation_id = conversation_id

        # 更新最后活动时间
        conversation.last_activity = datetime.utcnow()
        await self._save_conversation_metadata(conversation)

        # 更新数据库中的当前对话
        if self.db:
            self.db.switch_conversation(self.worker_id, conversation_id)

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

        # 更新数据库
        if self.db:
            self.db.update_conversation(conversation_id, {'name': new_name})

        self.logger.info(f"Renamed conversation {conversation_id} to '{new_name}'")

        return True

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的消息历史"""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return []

        sessions_dir = self._get_sessions_dir(conversation.project_path)
        messages_file = sessions_dir / conversation_id / "messages.jsonl"

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
        sessions_dir = self._get_sessions_dir(conversation.project_path)
        conv_dir = sessions_dir / conversation.id
        conv_dir.mkdir(parents=True, exist_ok=True)
        metadata_file = conv_dir / "metadata.json"

        with open(metadata_file, 'w') as f:
            json.dump(conversation.to_dict(), f, indent=2)


class OpenCodeConversationManager(BaseConversationManager):
    """OpenCode 的对话管理器实现"""

    def __init__(self, worker_id: str, db: Optional['DatabaseManager'] = None):
        self.worker_id = worker_id
        self.db = db
        self.current_conversation_id: Optional[str] = None
        self.conversations_cache: Dict[str, ConversationModel] = {}
        self.logger = get_app_logger()

        # 从数据库加载当前对话
        if self.db:
            self.current_conversation_id = self.db.get_current_conversation(worker_id)

    async def new_conversation(self, project_path: str, name: Optional[str] = None) -> str:
        """OpenCode 特定实现"""
        conversation_id = str(uuid.uuid4())
        project_path = os.path.abspath(project_path)

        conversation = ConversationModel(
            id=conversation_id,
            project_path=project_path,
            name=name or f"Conversation {conversation_id[:8]}"
        )

        self.conversations_cache[conversation_id] = conversation
        self.current_conversation_id = conversation_id

        # 保存到数据库
        if self.db:
            self.db.create_conversation({
                'id': conversation_id,
                'worker_id': self.worker_id,
                'project_path': project_path,
                'name': conversation.name,
                'created_at': conversation.created_at,
                'last_activity': conversation.last_activity,
                'is_current': True,
                'metadata': conversation.metadata
            })

        self.logger.info(f"Created new OpenCode conversation: {conversation_id} at {project_path}")

        return conversation_id

    async def clone_conversation(self, conversation_id: str, new_name: Optional[str] = None) -> str:
        """克隆对话（继承原对话的 project_path）"""
        original = await self.get_conversation(conversation_id)
        if not original:
            raise ValueError(f"Conversation not found: {conversation_id}")

        new_id = str(uuid.uuid4())

        cloned = ConversationModel(
            id=new_id,
            project_path=original.project_path,
            name=new_name or f"{original.name} (Copy)"
        )

        self.conversations_cache[new_id] = cloned

        # 保存到数据库
        if self.db:
            self.db.create_conversation({
                'id': new_id,
                'worker_id': self.worker_id,
                'project_path': original.project_path,
                'name': cloned.name,
                'created_at': cloned.created_at,
                'last_activity': cloned.last_activity,
                'is_current': False,
                'metadata': {'cloned_from': conversation_id, **cloned.metadata}
            })

        self.logger.info(f"Cloned OpenCode conversation {conversation_id} to {new_id}")

        return new_id

    async def list_conversations(self) -> List[ConversationModel]:
        """列出所有对话（从数据库或缓存）"""
        # 优先从数据库获取
        if self.db:
            db_conversations = self.db.list_conversations(self.worker_id)
            conversations = []
            for data in db_conversations:
                conversation = ConversationModel(
                    id=data['id'],
                    project_path=data.get('project_path', ''),
                    name=data.get('name'),
                    created_at=data.get('created_at'),
                    last_activity=data.get('last_activity'),
                    metadata=data.get('metadata', {})
                )
                self.conversations_cache[data['id']] = conversation
                conversations.append(conversation)
            return conversations

        # 如果没有数据库，返回缓存中的对话
        conversations = list(self.conversations_cache.values())
        conversations.sort(key=lambda c: c.last_activity, reverse=True)
        return conversations

    async def get_conversation(self, conversation_id: str) -> Optional[ConversationModel]:
        """获取指定对话"""
        # 先从缓存获取
        if conversation_id in self.conversations_cache:
            return self.conversations_cache[conversation_id]

        # 从数据库获取
        if self.db:
            data = self.db.get_conversation(conversation_id)
            if data:
                conversation = ConversationModel(
                    id=data['id'],
                    project_path=data.get('project_path', ''),
                    name=data.get('name'),
                    created_at=data.get('created_at'),
                    last_activity=data.get('last_activity'),
                    metadata=data.get('metadata', {})
                )
                self.conversations_cache[conversation_id] = conversation
                return conversation

        return None

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id not in self.conversations_cache:
            return False

        if conversation_id == self.current_conversation_id:
            raise ValueError("Cannot delete current conversation. Switch to another conversation first.")

        del self.conversations_cache[conversation_id]

        # 从数据库删除
        if self.db:
            self.db.delete_conversation(conversation_id)

        self.logger.info(f"Deleted OpenCode conversation: {conversation_id}")

        return True

    async def switch_conversation(self, conversation_id: str) -> bool:
        """切换到指定对话"""
        if conversation_id not in self.conversations_cache:
            raise ValueError(f"Conversation not found: {conversation_id}")

        self.current_conversation_id = conversation_id

        conversation = self.conversations_cache[conversation_id]
        conversation.last_activity = datetime.utcnow()

        # 更新数据库中的当前对话
        if self.db:
            self.db.switch_conversation(self.worker_id, conversation_id)

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

        # 更新数据库
        if self.db:
            self.db.update_conversation(conversation_id, {'name': new_name})

        self.logger.info(f"Renamed OpenCode conversation {conversation_id} to '{new_name}'")

        return True

    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """获取对话的消息历史 - 简化实现"""
        # OpenCode 的消息历史可能需要从其他地方获取
        return []
