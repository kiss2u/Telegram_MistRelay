from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QAbstractListModel, QModelIndex, QObject, Qt, Signal, Slot


class RoleListModel(QAbstractListModel):
    countChanged = Signal()

    def __init__(
        self,
        *,
        roles: list[str] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._roles: list[str] = list(roles or [])

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._items):
            return None

        if role < Qt.UserRole:
            return None

        role_index = role - Qt.UserRole - 1
        if role_index < 0 or role_index >= len(self._roles):
            return None

        return self._items[row].get(self._roles[role_index])

    def roleNames(self) -> dict[int, bytes]:
        return {
            Qt.UserRole + index + 1: role.encode("utf-8")
            for index, role in enumerate(self._roles)
        }

    def get_count(self) -> int:
        return len(self._items)

    def set_items(self, items: list[dict[str, Any]]) -> None:
        next_roles = self._derive_roles(items)
        self.beginResetModel()
        self._items = [dict(item) for item in items]
        self._roles = next_roles
        self.endResetModel()
        self.countChanged.emit()

    def clear(self) -> None:
        self.set_items([])

    def items(self) -> list[dict[str, Any]]:
        return list(self._items)

    def _derive_roles(self, items: list[dict[str, Any]]) -> list[str]:
        if self._roles:
            known = list(self._roles)
        else:
            known = []

        for item in items:
            for key in item.keys():
                if key not in known:
                    known.append(key)

        return known

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any]:
        if row < 0 or row >= len(self._items):
            return {}
        return dict(self._items[row])

    count = Property(int, get_count, notify=countChanged)
