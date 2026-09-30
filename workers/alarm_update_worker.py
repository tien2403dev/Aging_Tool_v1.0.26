from PyQt5.QtCore import QObject, QRunnable, pyqtSignal
from repositories.alarm_repository import AlarmRepository


class AlarmUpdateSignals(QObject):
    finished = pyqtSignal(object, bool, str)


class AlarmUpdateWorker(QRunnable):
    def __init__(self, database_path, expected, field, value):
        super().__init__()
        self.database_path = database_path
        self.expected = expected
        self.field = field
        self.value = value
        self.signals = AlarmUpdateSignals()

    def run(self):
        try:
            latest, conflict = AlarmRepository(self.database_path).update_tracking(
                self.expected, self.field, self.value
            )
            self.signals.finished.emit(latest, conflict, "")
        except Exception as error:
            self.signals.finished.emit(None, False, str(error))
