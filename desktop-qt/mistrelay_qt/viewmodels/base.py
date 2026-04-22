from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal


class BaseViewModel(QObject):
    busyChanged = Signal()
    errorMessageChanged = Signal()
    infoMessageChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._error_message = ""
        self._info_message = ""

    def _set_busy(self, value: bool) -> None:
        if self._busy == value:
            return
        self._busy = value
        self.busyChanged.emit()

    def _set_error_message(self, value: str) -> None:
        if self._error_message == value:
            return
        self._error_message = value
        self.errorMessageChanged.emit()

    def _set_info_message(self, value: str) -> None:
        if self._info_message == value:
            return
        self._info_message = value
        self.infoMessageChanged.emit()

    def get_busy(self) -> bool:
        return self._busy

    def get_error_message(self) -> str:
        return self._error_message

    def get_info_message(self) -> str:
        return self._info_message

    busy = Property(bool, get_busy, notify=busyChanged)
    errorMessage = Property(str, get_error_message, notify=errorMessageChanged)
    infoMessage = Property(str, get_info_message, notify=infoMessageChanged)
