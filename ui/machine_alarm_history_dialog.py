"""Display rule windows rebuilt from the currently loaded logs."""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QLabel, QTableWidget,
                            QTableWidgetItem, QPushButton, QAbstractItemView)


class MachineAlarmHistoryDialog(QDialog):
    def __init__(self, machine, slot, alarm_date, evidence, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Alarm History | {alarm_date} | {machine} - Slot {slot}")
        self.resize(1250, 650)
        self.evidence = evidence
        layout = QVBoxLayout(self)
        title = QLabel(f"Machine: {machine} | Slot: {slot} | Alarm Date: {alarm_date}")
        title.setTextFormat(Qt.PlainText)
        layout.addWidget(title)
        layout.addWidget(QLabel("Quy tắc / Model:"))
        self.rules = QComboBox()
        self.rules.setMinimumHeight(32)
        for item in evidence:
            label = item['reason']
            if item['model']:
                label += f" — {item['model']}"
            label += f" | {item['start']} → {item['end']}"
            self.rules.addItem(label)
        layout.addWidget(self.rules)
        self.summary = QLabel()
        self.summary.setTextFormat(Qt.PlainText)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            'No', 'Date', 'Time', 'Slot', 'Result', 'Model', 'PARTNO',
            'LOT NO', 'Interface', 'SCRAP CODE', 'Source file / line'])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)
        close = QPushButton('Close')
        close.clicked.connect(self.accept)
        layout.addWidget(close)
        self.rules.currentIndexChanged.connect(self.show_rule)
        self.show_rule(0)

    def show_rule(self, index):
        if not 0 <= index < len(self.evidence):
            return
        item = self.evidence[index]
        target = '—' if item['target'] is None else f"{item['target']:.2f}%"
        self.summary.setText(
            f"Total: {item['count']} | PASS: {item['passed']} | FAIL: {item['failed']} | "
            f"Yield: {item['yield_percent']:.2f}% | Target: {target}\n"
            f"Start: {item['start']} | End: {item['end']}")
        self.table.setRowCount(len(item['tests']))
        for i, test in enumerate(item['tests']):
            values = [i+1] + [test.get(key, '') for key in
                ('date', 'time', 'slot', 'result', 'model', 'partno', 'lotno', 'interface', 'scrapcode')]
            values.append(f"{test.get('file_name', '')} : {test.get('line_number', '')}")
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setTextAlignment(Qt.AlignCenter)
                if col == 4:
                    cell.setForeground(QColor('#15803D' if str(value).upper() == 'PASS' else '#DC2626'))
                self.table.setItem(i, col, cell)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
