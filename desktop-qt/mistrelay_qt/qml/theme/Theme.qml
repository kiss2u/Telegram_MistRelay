pragma Singleton

import QtQuick

QtObject {
    readonly property color colorPrimary: "#667eea"
    readonly property color colorPrimaryDark: "#5568d3"
    readonly property color colorPrimaryLight: "#7c8ef0"
    readonly property color colorSuccess: "#10b981"
    readonly property color colorWarning: "#f59e0b"
    readonly property color colorDanger: "#ef4444"
    readonly property color colorInfo: "#3b82f6"
    readonly property color textPrimary: "#0f172a"
    readonly property color textSecondary: "#64748b"
    readonly property color textTertiary: "#94a3b8"
    readonly property color surface: "#f8fafc"
    readonly property color panelSurface: "#ffffff"
    readonly property color surfaceMuted: "#eef2ff"
    readonly property color glassBg: "#d9ffffff"
    readonly property color glassBorder: "#2effffff"
    readonly property color sidebarStart: "#1e293b"
    readonly property color sidebarEnd: "#0f172a"
    readonly property color lineColor: "#e2e8f0"
    readonly property color successSoft: "#ecfdf5"
    readonly property color infoSoft: "#eff6ff"
    readonly property color warningSoft: "#fffbeb"
    readonly property color dangerSoft: "#fef2f2"
    readonly property color shadowColor: "#220f172a"

    readonly property int radiusSmall: 12
    readonly property int radiusMedium: 18
    readonly property int radiusLarge: 24
    readonly property int pagePadding: 28
    readonly property int cardPadding: 22
    readonly property int controlHeight: 48
    readonly property int sectionSpacing: 20
    readonly property int slowDuration: 280
    readonly property string fontFamily: "Segoe UI"
}
