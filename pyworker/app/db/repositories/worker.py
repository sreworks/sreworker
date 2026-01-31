"""Worker repository for database operations."""

import json
from typing import Optional, List
from .base import BaseRepository
from ..database_models.worker import WorkerDO


class WorkerRepository(BaseRepository):
    """Repository for Worker CRUD operations."""

    def create(self, worker: WorkerDO) -> bool:
        """
        Create a new worker record.

        Args:
            worker: WorkerDO instance

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("""
                INSERT INTO workers (id, type, env_vars, command_params, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, [
                worker.id,
                worker.type,
                json.dumps(worker.env_vars),
                json.dumps(worker.command_params),
                worker.created_at
            ])
            self.conn.commit()
            self.logger.info(f"Created worker record: {worker.id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create worker: {e}")
            return False

    def get(self, worker_id: str) -> Optional[WorkerDO]:
        """
        Get worker by ID.

        Args:
            worker_id: Worker ID

        Returns:
            WorkerDO instance or None
        """
        try:
            result = self.conn.execute("""
                SELECT id, type, env_vars, command_params, created_at
                FROM workers
                WHERE id = ?
            """, [worker_id]).fetchone()

            if result:
                return WorkerDO(
                    id=result[0],
                    type=result[1],
                    env_vars=json.loads(result[2]) if result[2] else {},
                    command_params=json.loads(result[3]) if result[3] else [],
                    created_at=result[4]
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get worker {worker_id}: {e}")
            return None

    def list_all(self) -> List[WorkerDO]:
        """
        List all workers.

        Returns:
            List of WorkerDO instances
        """
        try:
            results = self.conn.execute("""
                SELECT id, type, env_vars, command_params, created_at
                FROM workers
                ORDER BY created_at DESC
            """).fetchall()

            return [
                WorkerDO(
                    id=row[0],
                    type=row[1],
                    env_vars=json.loads(row[2]) if row[2] else {},
                    command_params=json.loads(row[3]) if row[3] else [],
                    created_at=row[4]
                )
                for row in results
            ]
        except Exception as e:
            self.logger.error(f"Failed to list workers: {e}")
            return []

    def delete(self, worker_id: str) -> bool:
        """
        Delete worker by ID.

        Args:
            worker_id: Worker ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.conn.execute("DELETE FROM workers WHERE id = ?", [worker_id])
            self.conn.commit()
            self.logger.info(f"Deleted worker record: {worker_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete worker: {e}")
            return False
