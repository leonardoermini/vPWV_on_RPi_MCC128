import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QDialog
from GUI_DialogTh import Ui_DialogThreshold

class DeltaXDialog(QDialog, Ui_DialogThreshold):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

if __name__ == "__main__":
    App = QApplication(sys.argv)
    Dial = DeltaXDialog()
    Dial.show()
    sys.exit(App.exec_())