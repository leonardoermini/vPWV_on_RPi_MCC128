// Copyright (C) 2021 The Qt Company Ltd.
// SPDX-License-Identifier: LicenseRef-Qt-Commercial OR GPL-3.0-only

import QtQuick 2.7
import QtQuick.Layouts 2.7
import QtQuick.VirtualKeyboard 2.7
import QtQuick.VirtualKeyboard.Components 2.7

KeyboardLayout {
    function createInputMethod() {
        return Qt.createQmlObject('import QtQuick; import QtQuick.VirtualKeyboard.Plugins; HandwritingInputMethod {}', parent)
    }
    sharedLayouts: ['symbols']

    KeyboardRow {
        KeyboardColumn {
            Layout.preferredWidth: 1
            InputModeKey {
            }
            ChangeLanguageKey {
                visible: true
            }
            ShiftKey {
            }
            HandwritingModeKey {
            }
        }
        KeyboardColumn {
            Layout.preferredWidth: 8
            TraceInputKey {
                objectName: "hwrInputArea"
                patternRecognitionMode: InputEngine.PatternRecognitionMode.Handwriting
            }
        }
        KeyboardColumn {
            Layout.preferredWidth: 1
            Key {
                key: Qt.Key_Period
                text: "."
                alternativeKeys: "<>()/\\\"'=+-_:;,.?! "
                smallText: "!?"
                smallTextVisible: true
                highlighted: true
            }
            HideKeyboardKey {
                visible: true
            }
            BackspaceKey {
            }
            EnterKey {
            }
        }
    }
}
