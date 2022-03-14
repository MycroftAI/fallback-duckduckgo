// Copyright 2021, Mycroft AI Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import QtQuick 2.4
import QtQuick.Controls 2.2
import QtQuick.Layouts 1.4
import org.kde.kirigami 2.4 as Kirigami
import QtGraphicalEffects 1.0
import Mycroft 1.0 as Mycroft

Mycroft.CardDelegate {
    id: root
    cardBackgroundOverlayColor: "black"

    Img {
        id: logo
        width: Mycroft.Units.gridUnit * 3
        height: Mycroft.Units.gridUnit * 3
        anchors.top: parent.top
        anchors.topMargin: Mycroft.Units.gridUnit

        imgSrc: Qt.resolvedUrl("images/ddg_black_bg.svg")
    }

    Title {
        id: articleTitle
        anchors.verticalCenter: logo.verticalCenter
        anchors.left: logo.right
        anchors.leftMargin: Mycroft.Units.gridUnit
        anchors.right: parent.right
        font.pixelSize: Mycroft.Units.gridUnit * 3
        font.styleName: "Bold"
        heightUnits: 4
        text: sessionData.title
        maxTextLength: 21
    }

    Img {
        width: parent.width
        height: parent.height - Mycroft.Units.gridUnit * 6
        anchors.horizontalCenter: articleTitle.horizontalCenter
        anchors.bottom: parent.bottom
        imgSrc: sessionData.imgLink
    }
}
