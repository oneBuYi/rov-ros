#!/usr/bin/env python3
"""Convert operation manual markdown to formatted Word document — scenario-driven v2.0."""

import os
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

doc = Document()

# -- Font configuration --
WESTERN_FONT = 'Times New Roman'
EAST_ASIAN_FONT = '宋体'


def set_run_font(run, size=None, bold=None, italic=None, color=None, western=None, ea=None):
    """Set both Western and East Asian fonts on a run."""
    wf = western or WESTERN_FONT
    ef = ea or EAST_ASIAN_FONT
    run.font.name = wf
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), ef)
    rFonts.set(qn('w:ascii'), wf)
    rFonts.set(qn('w:hAnsi'), wf)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color:
        run.font.color.rgb = color


def set_style_font(style, western=None, ea=None):
    """Set Western and East Asian fonts on a style."""
    wf = western or WESTERN_FONT
    ef = ea or EAST_ASIAN_FONT
    style.font.name = wf
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), ef)
    rFonts.set(qn('w:ascii'), wf)
    rFonts.set(qn('w:hAnsi'), wf)


# -- Default font --
style = doc.styles['Normal']
style.font.size = Pt(10.5)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.15
set_style_font(style)

# -- Configure heading styles --
BLUE_DARK = RGBColor(0x1A, 0x3C, 0x6E)
BLUE_MED = RGBColor(0x4A, 0x6E, 0xA8)
for i in range(1, 4):
    hs = doc.styles[f'Heading {i}']
    hs.font.color.rgb = BLUE_DARK
    set_style_font(hs)
    if i == 1:
        hs.font.size = Pt(22)
        hs.paragraph_format.space_before = Pt(24)
        hs.paragraph_format.space_after = Pt(12)
    elif i == 2:
        hs.font.size = Pt(16)
        hs.paragraph_format.space_before = Pt(18)
        hs.paragraph_format.space_after = Pt(8)
    else:
        hs.font.size = Pt(13)
        hs.paragraph_format.space_before = Pt(12)
        hs.paragraph_format.space_after = Pt(6)

# -- Configure List Bullet style font --
try:
    from docx.enum.style import WD_STYLE_TYPE
    lb = doc.styles['List Bullet']
except KeyError:
    lb = doc.styles.add_style('List Bullet', WD_STYLE_TYPE.PARAGRAPH)
set_style_font(lb)


def add_code_block(doc, text, font_size=9):
    """Add a styled code block (monospaced Consolas)."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.name = 'Consolas'
    run.font.size = Pt(font_size)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    pPr = p._p.get_or_add_pPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F0F0" w:val="clear"/>')
    pPr.append(shd)


def add_placeholder_box(doc, description):
    """Add an image placeholder box with dashed border."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell_p = cell.paragraphs[0]
    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cell_p.add_run(f'[IMG]  {description}')
    run.font.size = Pt(9)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
    cell.width = Inches(5.5)
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        '<w:top w:val="dashed" w:sz="4" w:color="999999"/>'
        '<w:left w:val="dashed" w:sz="4" w:color="999999"/>'
        '<w:bottom w:val="dashed" w:sz="4" w:color="999999"/>'
        '<w:right w:val="dashed" w:sz="4" w:color="999999"/>'
        '</w:tcBorders>'
    )
    tcPr.append(borders)
    doc.add_paragraph()


import pathlib
BASE_DIR = pathlib.Path(__file__).resolve().parent

def add_image(doc, image_path, width_inches=5.5):
    """Add an image centered on the page."""
    if not os.path.isabs(image_path):
        image_path = str(BASE_DIR / image_path)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(image_path, width=Inches(width_inches))
    doc.add_paragraph()


def add_table(doc, headers, rows):
    """Add a formatted table with header styling and alternating row colors."""
    tbl = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = tbl.cell(0, i)
        cell_p = cell.paragraphs[0]
        run = cell_p.add_run(h)
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="1A3C6E" w:val="clear"/>')
        tcPr.append(shd)
    for r, row_data in enumerate(rows):
        for c, val in enumerate(row_data):
            cell = tbl.cell(r + 1, c)
            cell_p = cell.paragraphs[0]
            run = cell_p.add_run(str(val))
            run.font.size = Pt(9)
            if r % 2 == 1:
                tcPr = cell._tc.get_or_add_tcPr()
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="EEF2F7" w:val="clear"/>')
                tcPr.append(shd)
    doc.add_paragraph()


def add_checklist(doc, items):
    """Add bullet list items."""
    for item in items:
        p = doc.add_paragraph(style='List Bullet')
        run = p.add_run(item)
        run.font.size = Pt(10)


def add_warning(doc, text):
    """Add a bold warning paragraph."""
    p = doc.add_paragraph()
    run = p.add_run(f'WARNING: {text}')
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0xCC, 0x55, 0x00)


def add_note(doc, text):
    """Add an italic note."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def add_bold(doc, text):
    """Add a bold paragraph."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    return p


def add_numbered(doc, items):
    """Add numbered list."""
    for i, s in enumerate(items, 1):
        p = doc.add_paragraph()
        run = p.add_run(f'{i}. {s}')
        run.font.size = Pt(10)


def add_flow(doc, lines):
    """Add a flow chart as monospaced text."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    text = '\n'.join(lines)
    run = p.add_run(text)
    run.font.name = 'Consolas'
    run.font.size = Pt(8.5)


# ==================== TITLE PAGE ====================
for _ in range(3):
    doc.add_paragraph()

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('水下机器人池壁检测系统')
run.font.size = Pt(32)
run.bold = True
run.font.color.rgb = BLUE_DARK

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('操作手册')
run.font.size = Pt(24)
run.font.color.rgb = BLUE_MED

doc.add_paragraph()

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
info.add_run('版本 v2.0  |  面向操作员  |  2026年8月').font.size = Pt(11)

doc.add_paragraph()
doc.add_paragraph()

note = doc.add_paragraph()
note.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = note.add_run('使用前请先阅读本手册的「首次部署」和「应急处理」章节')
run.font.size = Pt(10)
run.font.italic = True

doc.add_page_break()

# ==================== CH1: FIRST DEPLOYMENT ====================
doc.add_heading('1. 首次部署', level=1)

doc.add_paragraph(
    '首次部署是将水下机器人从开箱到系统就绪的完整流程。完成本章后，操作员即可开始执行巡检任务。'
)

# 1.1
doc.add_heading('1.1 开箱检查', level=2)
doc.add_paragraph('在启动系统前，按以下清单逐项确认：')
add_checklist(doc, [
    '水下机器人电池：已充满或电量充足',
    '水下机器人水密：舱盖密封圈清洁无杂物，舱盖锁紧',
    '线缆连接：水下机器人与岸上笔记本之间的线缆完好',
    '摄像头：镜头清洁无遮挡',
    'UGPS 基站：岸上 UGPS 基站已部署并通电',
])

# 1.2
doc.add_heading('1.2 系统接线', level=2)
doc.add_paragraph(
    '水下机器人通过线缆与岸上操作员的笔记本连接，实现控制指令和数据的传输。'
)
add_table(doc,
    ['条件', '要求'],
    [
        ['笔记本', '任意操作系统（Windows / macOS / Linux），有浏览器'],
        ['浏览器', 'Chrome / Edge / Firefox 等现代浏览器'],
        ['网络', '笔记本通过网线连接水下机器人（IP：192.168.137.100）'],
    ])

doc.add_paragraph('接线步骤：')
add_numbered(doc, [
    '将线缆一端连接水下机器人',
    '将线缆另一端（网口）连接笔记本',
    '确认 UGPS 基站已通电',
])

doc.add_paragraph('线缆分为电力线和信号线，接线说明如下：')

add_bold(doc, '电力线')
doc.add_paragraph('为水下机器人供电，三芯接线：')
add_image(doc, '材料/图片/电力线.jpg', width_inches=5.5)
add_checklist(doc, [
    '红色接火线',
    '黑色接零线',
    '蓝色接地线',
])

add_bold(doc, '信号线')
doc.add_paragraph('水下机器人与地面控制中心的通信连接：')
add_image(doc, '材料/图片/信号线.jpg', width_inches=5.5)
doc.add_paragraph('两根黄绿色信号线，无极性，可反接。')

# 1.3
doc.add_heading('1.3 上电启动', level=2)
doc.add_paragraph(
    '水下机器人上电后系统自动启动，无需手动操作。等待约 30 秒后，在笔记本浏览器中打开控制页面。'
)
doc.add_paragraph(
    '若系统未能自动启动（浏览器无法打开页面），将水下机器人断电重启即可。'
)

# 1.4
doc.add_heading('1.4 打开控制页面', level=2)
add_numbered(doc, [
    '在笔记本浏览器地址栏输入：https://192.168.137.100:8000',
    '首次访问会弹出安全警告（自签名证书），点击 "高级" → "继续访问（不安全）" 即可。此后浏览器会记住信任。',
    '页面加载后，操作员将看到地面控制中心主界面。',
])
add_image(doc, '材料/图片/browser-cert-warning.png', width_inches=5.5)
add_image(doc, '材料/图片/browser-cert-advanced.png', width_inches=5.5)

# 1.5
doc.add_heading('1.5 界面导览', level=2)
doc.add_paragraph(
    '地面控制中心 Web 界面是操作员与水下机器人交互的唯一入口。了解各区域的功能是后续操作的基础。'
)
add_image(doc, '材料/图片/gcs-main-overview.png', width_inches=5.5)

add_table(doc,
    ['编号', '区域名称', '做什么用'],
    [
        ['①', '视频画面', '实时水下摄像头画面，观察池壁状态和水下环境'],
        ['②', '遥测面板', '实时数据：深度、航向、GPS、当前/目标网格、目标距离、深度偏差'],
        ['③', '网格面板', '输入目标网格行列号，查看当前位置与目标网格距离'],
        ['④', '摇杆操控区', '游戏手柄操控（浏览器界面显示为虚拟摇杆）'],
        ['⑤', '控制面板', '在线调节 PID 参数，设定定深/定航目标值，开关灯，调节电机增益'],
        ['⑥', '状态栏', '连接状态、定深/航向锁定状态、经纬度、偏航角、PID 输出'],
    ])

doc.add_paragraph('以下对各区域做简要说明，详细操作见第 2 章。')

add_bold(doc, '视频画面')
doc.add_paragraph(
    '视频画面为全屏显示，水下摄像头的 MJPEG 实时画面铺满整个浏览器窗口。'
    '遥测面板、网格面板、摇杆操控区、控制面板、状态栏等组件叠加在视频画面之上，延迟约 1-2 秒属于正常现象。'
)

add_bold(doc, '遥测面板')
doc.add_paragraph('显示水下机器人的运行状态数据：')
add_table(doc,
    ['指标', '含义', '所属面板'],
    [
        ['深度 (Depth)', '当前水深（m），正值向下', '遥测面板'],
        ['航向 (Yaw)', '当前朝向（°），0=正北', '遥测面板'],
        ['纬度 (Lat) / 经度 (Lon)', 'WGS84 坐标', '状态栏'],
        ['垂直 PWM', '深度 PID 推力输出（-100~100），正值=上升', '遥测面板'],
        ['偏航 PWM', '航向 PID 转向输出（-100~100），正值=右转', '遥测面板'],
        ['当前网格', '水下机器人最接近的网格编号（R行C列）', '网格面板'],
        ['目标网格', '任务设定的目标网格编号', '网格面板'],
        ['目标距离', '水下机器人到目标网格的水平距离（m）', '网格面板'],
        ['深度偏差', '当前深度与目标网格深度的差值（m）', '网格面板'],
    ])

doc.add_paragraph(
    '网格面板用于输入目标网格行列号，查看当前位置与目标网格的距离和深度偏差。'
)

add_bold(doc, '摇杆操控区')
doc.add_paragraph(
    '浏览器界面提供虚拟摇杆，操作逻辑与游戏手柄一致：'
)
add_table(doc,
    ['操控端', '控制功能', '说明'],
    [
        ['左摇杆', '前进/后退、左转/右转', '上下 = 前进后退，左右 = 偏航旋转'],
        ['右摇杆', '上升/下降、左横移/右横移', '上下 = 升降，左右 = 横移'],
    ])
add_note(doc, '实际操控时以游戏手柄为主，虚拟摇杆在浏览器界面上作为备选。两者操控逻辑完全相同。')
add_image(doc, '材料/图片/手柄.png', width_inches=5.5)
doc.add_paragraph(
    '摇杆信号中断超过 500ms 时，系统自动发送零值指令，电机停止，防止失控。恢复操作后自动恢复控制。'
)
doc.add_paragraph(
    '开关灯、调节电机增益的按钮在控制面板中操作（见下方控制面板说明）。'
)

add_bold(doc, '控制面板')
doc.add_paragraph(
    '在线调整深度/航向 PID 的 Kp/Ki/Kd，设定定深/定航目标值，开关灯，调节电机增益。'
    '修改参数后点击 Apply 即时生效。'
)

add_bold(doc, '状态栏')
doc.add_paragraph(
    '显示连接状态（已连接/未连接）、Arm 状态（已解锁/已锁定）、定深锁定和航向锁定指示灯、经纬度、偏航角、PID 输出值。'
)

# 1.6
doc.add_heading('1.6 确认系统就绪', level=2)
doc.add_paragraph('页面加载后，逐一检查：')
add_table(doc,
    ['检查项', '正常状态', '异常处理'],
    [
        ['连接状态', '状态栏显示"已连接"', '断电重启水下机器人'],
        ['视频画面', '实时水下画面显示', '检查摄像头连接'],
        ['深度数据', '深度数值正常', '等待飞控初始化'],
    ])

add_image(doc, '材料/图片/gcs-status-ok.png', width_inches=5.5)
doc.add_paragraph('全部检查通过后，系统已就绪，可以开始执行巡检任务。')

# ==================== CH2: DAILY INSPECTION ====================
doc.add_page_break()
doc.add_heading('2. 日常巡检', level=1)

doc.add_paragraph('日常巡检是操作员最常执行的场景，完整流程如下：')
add_flow(doc, [
    '      巡检前准备',
    '         │',
    '         ▼',
    '    Arm 解锁',
    '         │',
    '         ▼',
    '  吊放下水',
    '         │',
    '         ▼',
    '  开启水下定位',
    '         │',
    '         ▼',
    '  设定定深 + 航向锁定',
    '         │',
    '         ▼',
    '  设定目标网格',
    '         │',
    '         ▼',
    '  导航至目标点（看遥测数据）',
    '         │',
    '         ▼',
    '  到达目标 → 观测/记录',
    '         │',
    '         ▼',
    '  下一网格（重复）或 返航关机',
])
doc.add_paragraph('以下各节按此流程逐一说明。')

# 2.1
doc.add_heading('2.1 巡检前准备', level=2)
doc.add_paragraph('此步骤与首次部署的检查和启动流程一致，简列如下：')
add_numbered(doc, [
    '确认电池、水密、线缆、摄像头、UGPS 基站状态正常（详见 §1.1）',
    '水下机器人上电，等待约 30 秒',
    '浏览器打开 https://192.168.137.100:8000',
    '确认连接状态、视频、GPS、深度数据正常（详见 §1.6）',
])
add_note(doc, '若此前已完成首次部署且未断开连接，可直接从上一次关闭后的状态继续，跳过大部分准备步骤。')

# 2.2
doc.add_heading('2.2 Arm 解锁', level=2)
doc.add_paragraph('Arm（解锁）启用飞控电机输出，水下机器人才能响应操控。')
add_checklist(doc, [
    '点击状态栏的 "Arm" 按钮',
    '状态栏显示 "已解锁" 表示 Arm 成功',
    '若无法 Arm，断电重启水下机器人，等待约 30 秒后重试',
])
add_warning(doc, 'Arm 后水下机器人立即响应摇杆指令。在水面以上不要推动摇杆，防止电机空转。')
# Side-by-side Arm images
tbl = doc.add_table(rows=1, cols=2)
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
for idx, (img, label) in enumerate([
    ('材料/图片/disarmed-state.png', 'Arm 解锁前（绿色 Arm 按钮）'),
    ('材料/图片/armed-state.png', 'Arm 解锁后（红色 Disarm 按钮）'),
]):
    cell = tbl.cell(0, idx)
    cell_p = cell.paragraphs[0]
    cell_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cell_p.add_run()
    if not os.path.isabs(img):
        img = str(BASE_DIR / img)
    run.add_picture(img, width=Inches(1.77))
    # Caption below image
    cap_p = cell.add_paragraph()
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_run = cap_p.add_run(label)
    cap_run.font.size = Pt(9)
    cap_run.font.italic = True
    cap_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
doc.add_paragraph()

# 2.3
doc.add_heading('2.3 吊放下水', level=2)
doc.add_paragraph(
    'Arm 后，使用吊机将水下机器人吊放入水。入水后，通过虚拟摇杆操控水下机器人移动到目标区域。'
    '摇杆各轴含义及功能按钮说明见 §1.5 界面导览中摇杆操控区的介绍。'
)

add_bold(doc, '安全保护：摇杆超时')
doc.add_paragraph(
    '如果摇杆信号中断超过 500ms，系统自动发送零值指令（x=0, y=0, z=0, r=0），电机立即停止。'
    '操作员恢复操控后自动恢复控制。此保护用于防止通信中断时水下机器人失控。'
)

add_image(doc, '材料/图片/吊放下水.jpg', width_inches=5.5)

# 2.4
doc.add_heading('2.4 开启水下定位', level=2)
doc.add_paragraph(
    '吊放下水后，开启水下定位设备（UGPS）以获取水下机器人的实时位置。'
)
add_bold(doc, '操作步骤：')
add_numbered(doc, [
    '打开 SeaTrac PinPoint 软件',
    '进行相应设置，连接水下机器人',
])
add_image(doc, '材料/图片/ugps1.png', width_inches=5.5)
add_image(doc, '材料/图片/ugps2.png', width_inches=5.5)
p = doc.add_paragraph()
run = p.add_run('3. 确认定位成功开启')
run.font.size = Pt(10)
add_image(doc, '材料/图片/ugps3.png', width_inches=5.5)

# 2.5
doc.add_heading('2.5 设定定深', level=2)
doc.add_paragraph('定深功能使水下机器人自动维持在设定的目标深度，无需手动调节升降杆。')
add_bold(doc, '操作步骤：')
add_numbered(doc, [
    '在 控制面板的深度控制区，输入目标深度值（米，正值 = 水下深度）',
    '点击 "Set Depth" 按钮',
    '状态栏 "Depth Hold" 指示灯亮起，系统开始自动维持深度',
    '要关闭定深：点击 "Toggle Hold" 按钮，水下机器人恢复手动升降控制',
    '要以当前深度为新目标：先关闭再打开 Toggle Hold，系统自动将当前深度设为目标值',
])
add_image(doc, '材料/图片/定深.png', width_inches=5.5)

# 2.6
doc.add_heading('2.6 设定航向锁定', level=2)
doc.add_paragraph('航向锁定使水下机器人自动维持在设定的朝向角度，无需手动调节偏航。')
add_bold(doc, '操作步骤：')
add_numbered(doc, [
    '在 控制面板的航向控制区，输入目标航向值（0° ~ 360°，0° = 正北）',
    '点击 "Set Heading" 按钮',
    '状态栏 "Heading Hold" 指示灯亮起',
    '关闭/切换方式与定深相同（"Toggle Hold" 按钮）',
])
add_image(doc, '材料/图片/定航.png', width_inches=5.5)
doc.add_paragraph(
    '定深和航向锁定可同时开启。开启后操作员只需操控 X/Y 横移和前进，深度和朝向由系统自动保持。'
)

# 2.7
doc.add_heading('2.7 设定目标网格', level=2)
doc.add_paragraph(
    '定深和航向锁定开启后，水下机器人已稳定在目标深度和朝向。接下来设定巡检的目标网格。'
)
add_image(doc, '材料/图片/网格全览.png', width_inches=5.5)

doc.add_paragraph('池壁检测区域被划分为网格，每个网格点有唯一的行号-列号编号：')

# 网格图 + 说明文字 左右并列
tbl = doc.add_table(rows=1, cols=2)
tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
# 左列：说明文字
cell_left = tbl.cell(0, 0)
cell_left.paragraphs[0].clear()
for item in [
    '行号 (Row)：0 = 最靠近水面，数字越大越深',
    '列号 (Col)：0 = 最左，数字越大越靠右',
    '每个网格点已预设有 GPS 坐标和深度值（由技术人员预先配置）',
]:
    p = cell_left.add_paragraph(style='List Bullet')
    run = p.add_run(item)
    run.font.size = Pt(10)
# 右列：网格.png（垂直居中）
cell_right = tbl.cell(0, 1)
cell_right.paragraphs[0].clear()
cell_right.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
cell_right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
run = cell_right.paragraphs[0].add_run()
img_path = str(BASE_DIR / '材料/图片/网格.png') if not os.path.isabs('材料/图片/网格.png') else '材料/图片/网格.png'
run.add_picture(img_path, width=Inches(2.5))
doc.add_paragraph()

add_bold(doc, '操作步骤：')
p1 = doc.add_paragraph()
p1.add_run('1. 在网格面板输入目标行号（Row）和目标列号（Col）').font.size = Pt(10)
p2 = doc.add_paragraph()
p2.add_run('2. 点击 "设定" 按钮').font.size = Pt(10)

# 网格设定 + 目标网格距离 并列（相同高度）
tbl2 = doc.add_table(rows=1, cols=2)
tbl2.alignment = WD_TABLE_ALIGNMENT.CENTER
for idx, img_file in enumerate(['材料/图片/网格设定.png', '材料/图片/目标网格距离.png']):
    cell = tbl2.cell(0, idx)
    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cell.paragraphs[0].add_run()
    p = str(BASE_DIR / img_file) if not os.path.isabs(img_file) else img_file
    run.add_picture(p, height=Inches(0.9))
doc.add_paragraph()

p3 = doc.add_paragraph()
run = p3.add_run('3. 遥测面板立即显示：目标网格（如 "R0C3"）、目标距离（到目标的水平距离）、深度偏差（当前深度与目标深度的差值）')
run.font.size = Pt(10)

# 2.8
doc.add_heading('2.8 导航至目标点', level=2)
doc.add_paragraph('设定目标网格后，参照遥测面板的两个关键数据操控导航：')
add_table(doc,
    ['关键数据', '目标值', '说明'],
    [
        ['目标距离', '越小越好，< 0.5m 判定到达', '通过 X/Y 摇杆水平移动缩小'],
        ['深度偏差', '越小越好，< 0.2m 判定到达', '由定深自动保持（见 §2.5），偏差过大时需调整'],
    ])

add_bold(doc, '操作要领：')
add_checklist(doc, [
    '观察目标距离数值，操作 X/Y 摇杆向目标方向移动',
    '观察深度偏差，若偏差持续偏大，检查定深设定或重新设定深度',
    '同时满足以下条件时，到达目标指示灯亮起：水平距离 < 0.5m（可配置），深度偏差 < 0.2m（可配置）',
])
add_image(doc, '材料/图片/前往目标网格.png', width_inches=5.5)
add_image(doc, '材料/图片/到达目标网格.png', width_inches=5.5)
doc.add_paragraph(
    '另外，遥测面板显示当前网格的自动识别结果，即使未设定目标网格，也可用于快速定位水下机器人所在区域。'
)

# 2.8
doc.add_heading('2.9 观测与记录', level=2)
doc.add_paragraph('到达目标网格后：')
add_checklist(doc, [
    '观察视频画面，查看池壁状况（裂缝、附着物、结构完整性等）',
    '可微调摇杆以获取更清晰的观察角度',
])
add_note(doc, '视频以 MJPEG 推流，延迟约 1-2 秒属正常。若画面长时间冻结，刷新页面。')
doc.add_paragraph('点击记录按钮可保存当前遥测数据（CSV）和截图（JPG）：')
add_image(doc, '材料/图片/选择数据保存位置.png', width_inches=5.5)
add_image(doc, '材料/图片/保存数据内容.png', width_inches=5.5)
add_image(doc, '材料/图片/点击记录.png', width_inches=5.5)
add_image(doc, '材料/图片/记录成功.png', width_inches=5.5)
doc.add_paragraph('记录的文件可在资源管理器中查看：')
add_image(doc, '材料/图片/记录数据.png', width_inches=5.5)

# 2.9
doc.add_heading('2.10 继续下一网格', level=2)
doc.add_paragraph('当前网格观测完成后，重复 §2.7 - §2.9：')
add_numbered(doc, [
    '设定下一个目标网格（如当前 R0C0 → 下一格 R0C1）',
    '导航至目标点',
    '观测与记录',
])
doc.add_paragraph('典型巡检路线（池壁从水面线向下，自左向右逐列）：')
add_code_block(doc,
    'R0: C0 → C1 → C2 → C3 → C4 → C5\n'
    'R1: C0 → C1 → C2 → C3 → C4 → C5\n'
    'R2: C0 → C1 → C2 → C3 → C4 → C5\n'
    '...（逐行向下）'
)
doc.add_paragraph('实际巡检范围根据任务需求选择特定的行列范围。')

# 2.11
doc.add_heading('2.11 返航与关机', level=2)
doc.add_paragraph('完成巡检任务后，按以下顺序关闭系统：')
add_table(doc,
    ['步骤', '操作', '说明'],
    [
        ['1. Disarm', '点击 "Disarm" 按钮', '锁定电机，防止误操作'],
        ['2. 关闭浏览器页面', '关闭标签页即可', '无需数据保存'],
        ['3. 水下机器人断电', '出水后断开电池', '先出水再断电'],
    ])
add_warning(doc, '水中 Disarm 会导致失去推力，确保水下机器人处于安全状态后再操作。')
doc.add_paragraph(
    '快速重启：若需重新启动（如更换电池后），水下机器人重新上电即可，等待约 30 秒后刷新浏览器页面。'
)

# ==================== CH3: EMERGENCY ====================
doc.add_page_break()
doc.add_heading('3. 应急处理', level=1)

# 3.1
doc.add_heading('3.1 通信中断', level=2)
add_bold(doc, '现象：状态栏显示"未连接"，遥测数据冻结，视频停止。')
add_bold(doc, '自动行为：')
add_checklist(doc, [
    '摇杆超时保护触发（500ms）→ 电机停止',
    '定深/航向锁定失效',
    '系统每 3 秒自动尝试重连',
])
add_bold(doc, '应对：')
add_numbered(doc, [
    '不要惊慌 — 水下机器人失去指令后自然漂浮（取决于浮力配平）',
    '检查线缆连接是否松动',
    '刷新浏览器页面',
    '若持续无法连接，将水下机器人断电重启',
])

# 3.2
doc.add_heading('3.2 视频画面丢失', level=2)
add_bold(doc, '现象：视频区域黑屏或无画面更新。')
add_bold(doc, '排查步骤：')
add_numbered(doc, [
    '刷新浏览器页面',
    '检查摄像头线缆是否松动（需现场人员协助）',
    '视频画面丢失不影响其他功能（摇杆、遥测等仍然正常），可继续操控返航',
])

# 3.3
doc.add_heading('3.3 深度异常', level=2)
add_bold(doc, '现象：定深开启后水下机器人持续上升或下沉，无法稳定在目标深度。')
add_table(doc,
    ['可能原因', '排查方式', '解决'],
    [
        ['PID 参数不合适', '观察垂直 PWM 是否在 ±100 大幅摆动', '调整 Kp/Ki/Kd 参数（在控制面板中调整）'],
        ['浮力配平偏移', '关闭定深后也持续上浮/下沉', '物理调整配重，停止操作'],
        ['深度传感器异常', '深度数值跳变或明显不合理', '断电重启水下机器人'],
    ])

# 3.4
doc.add_heading('3.4 遥控器接管', level=2)
doc.add_paragraph(
    '如果操作员使用物理遥控器（如 FrSky），飞控优先响应遥控器信号。'
)
add_checklist(doc, [
    '切换到遥控器：直接使用物理遥控器，地面控制中心摇杆输入自动被忽略，遥测数据仍实时显示',
    '切回地面控制中心：关闭遥控器或切换到地面控制中心控制模式，摇杆恢复控制',
])

# 3.5
doc.add_heading('3.5 常见故障速查', level=2)
add_table(doc,
    ['现象', '可能原因', '解决'],
    [
        ['浏览器打不开地面控制中心页面', '水下机器人未上电或网络不通', '确认上电，检查线缆'],
        ['状态栏显示"未连接"', '系统自启动失败', '断电重启水下机器人'],
        ['无法 Arm', '飞控自检未通过', '断电重启，等约 30 秒后重试'],
        ['水下机器人不响应摇杆', '未 Arm 或电机故障', '检查 Arm 状态灯'],
        ['UGPS 数据为 0', '水下机器人未下水或水声定位未建立', '确认水下机器人已下水，等待 1-3 分钟定位建立'],
    ])

# 3.6
doc.add_heading('3.6 摇杆按钮速查', level=2)
add_table(doc,
    ['按钮位', '功能', '触发方式'],
    [
        ['Bit 0-10', '（预留）', '—'],
        ['Bit 11', '电机增益 +25%', '短按'],
        ['Bit 12', '电机增益 -25%', '短按'],
        ['Bit 13', '照明灯关闭', '短按'],
        ['Bit 14', '照明灯开启', '短按'],
        ['Bit 15', '（预留）', '—'],
    ])

# 3.7
doc.add_heading('3.7 关键指标参考', level=2)
add_table(doc,
    ['指标', '正常范围', '说明'],
    [
        ['深度', '0 ~ 10 m', '取决于池壁深度'],
        ['航向', '0° ~ 360°', '0°=正北，90°=正东，180°=正南，270°=正西'],
        ['垂直 PWM', '-100 ~ +100', '正值=上升，负值=下降'],
        ['目标距离', '0 ~ ∞', '< 1m 接近目标，< 0.5m 到达'],
        ['深度偏差', '0 ~ ∞', '< 1m 接近目标，< 0.2m 到达'],
        ['电机增益', '25% ~ 100%', '默认 50%'],
        ['定深默认 Kp/Ki/Kd', '100.0 / 40.0 / 80.0', '在控制面板中调整'],
        ['网络地址', 'https://192.168.137.100:8000', '地面控制中心页面'],
    ])

# 3.8
doc.add_heading('3.8 记录文件示例', level=2)
doc.add_paragraph(
    '巡检过程中点击"记录"按钮会保存当前遥测数据（CSV）和截图（JPG），文件保存在所选目录。操作步骤详见 §2.9。'
)

# ==================== END ====================
doc.add_paragraph()
doc.add_paragraph()
end_p = doc.add_paragraph()
end_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = end_p.add_run('— 文档结束 · 水下机器人池壁检测系统操作手册 v2.0 —')
run.font.size = Pt(10)
run.font.italic = True
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

# ===== FINAL FONT FIX: ensure every non-code run has correct Chinese/Western fonts =====
KEEP_MONO = {'Consolas', 'Courier New', 'Courier', 'monospace'}

for para in doc.paragraphs:
    for run in para.runs:
        rPr = run._element.find(qn('w:rPr'))
        if rPr is None:
            rPr = parse_xml(f'<w:rPr {nsdecls("w")}/>')
            run._element.insert(0, rPr)
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
            rPr.insert(0, rFonts)
        ascii_font = rFonts.get(qn('w:ascii'), '')
        if ascii_font and ascii_font in KEEP_MONO:
            continue
        rFonts.set(qn('w:ascii'), 'Times New Roman')
        rFonts.set(qn('w:hAnsi'), 'Times New Roman')
        rFonts.set(qn('w:eastAsia'), '宋体')
        rFonts.set(qn('w:cs'), 'Times New Roman')

for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    rPr = run._element.find(qn('w:rPr'))
                    if rPr is None:
                        rPr = parse_xml(f'<w:rPr {nsdecls("w")}/>')
                        run._element.insert(0, rPr)
                    rFonts = rPr.find(qn('w:rFonts'))
                    if rFonts is None:
                        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
                        rPr.insert(0, rFonts)
                    ascii_font = rFonts.get(qn('w:ascii'), '')
                    if ascii_font and ascii_font in KEEP_MONO:
                        continue
                    rFonts.set(qn('w:ascii'), 'Times New Roman')
                    rFonts.set(qn('w:hAnsi'), 'Times New Roman')
                    rFonts.set(qn('w:eastAsia'), '宋体')
                    rFonts.set(qn('w:cs'), 'Times New Roman')

# ===== SAVE =====
output_path = os.path.join(BASE_DIR, '水下机器人操作手册.docx')
os.makedirs(os.path.dirname(output_path), exist_ok=True)
doc.save(output_path)
print(f'Word document saved to: {output_path}')
