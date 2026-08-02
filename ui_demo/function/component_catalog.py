# -*- coding: utf-8 -*-
"""UIKit 组件橱窗目录（纯数据，不依赖 PySide6）。

目录内容与 ``ui/pages/__init__.py`` 的 ``NAV`` 注册表一一对应
（分类标题 + 页面标题），供服务层在不导入 UI 模块的前提下
对外提供「可演示组件清单」。新增/调整演示页时必须同步更新本文件。
"""

#: [(分类标题, [页面标题, ...]), ...]，顺序与 ui.pages.NAV 一致
COMPONENT_CATALOG = [
    ("设计令牌", [
        "设计令牌总览",
    ]),
    ("布局预设", [
        "顶部导航栏", "圣杯布局", "卡片网格", "单列堆叠", "侧边栏布局",
        "列表-详情", "分栏面板", "仪表盘网格", "英雄区", "居中容器",
        "瀑布流", "图文左右",
    ]),
    ("组件 · 输入", [
        "Button 按钮", "IconButton 图标按钮", "CheckBox 复选框",
        "RadioButton 单选框", "Switch 开关", "LineEdit 输入框",
        "TextArea 文本域", "SpinBox 数字框", "ComboBox 下拉框",
        "Slider 滑块", "DatePicker 日期", "TimePicker 时间",
        "Rating 评分", "ColorPicker 颜色", "AutoComplete 自动完成",
        "Cascader 级联选择", "Transfer 穿梭框", "UploadWidget 上传",
        "SegmentedControl 分段", "FormLayout 表单",
    ]),
    ("组件 · 展示", [
        "Avatar 头像", "Badge 徽标", "Card 卡片", "Descriptions 描述列表",
        "ListWidget 列表", "Table 表格", "Tree 树", "Timeline 时间轴",
        "Statistic 统计数值", "Calendar 日历", "Carousel 走马灯",
        "ImageView 图片", "QRCodeView 二维码", "CommentView 评论",
        "Collapse 折叠面板", "Empty 空状态", "Tooltip 工具提示",
        "Popover 气泡卡片",
    ]),
    ("组件 · 反馈", [
        "Tabs 标签页", "Anchor 锚点", "Breadcrumb 面包屑",
        "DropdownButton 下拉菜单", "NavMenu 侧边导航", "PageHeader 页头",
        "Pagination 分页", "Steps 步骤条", "Alert 警告提示",
        "Dialog 对话框", "Drawer 抽屉", "Notification 通知提醒",
        "Message 全局提示", "Popconfirm 气泡确认", "ResultView 结果页",
        "Skeleton 骨架屏", "Spinner 加载中", "ProgressBar 进度条",
        "Tour 漫游引导",
    ]),
    ("动画 · 属性", [
        "属性动画（28）",
    ]),
    ("动画 · 自绘", [
        "自绘动画（24）",
    ]),
    ("基础控件", [
        "基础控件全家福",
    ]),
    ("图表", [
        "图表（原生引擎）",
    ]),
    ("蓝图", [
        "蓝图（节点图）",
    ]),
]
