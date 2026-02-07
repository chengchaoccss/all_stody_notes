import type { TestRecord } from '../types';

// Placeholder images using picsum.photos for realistic demo
export const mockTestRecords: TestRecord[] = [
  {
    id: 'tc-001',
    screenshotUrl: 'https://picsum.photos/seed/test1/800/600',
    expectedResult: {
      type: 'image',
      imageUrl: 'https://picsum.photos/seed/expect1/800/600',
    },
    aiAnalysis:
      '页面整体布局与预期一致。导航栏高度为 64px，与设计稿吻合。主要内容区域的 **左侧边距偏移了 4px**，但仍在可接受范围内。所有按钮状态（默认、悬停、禁用）渲染正确，色值与设计规范一致。字体渲染使用了 SF Pro Display，行高 1.5，符合规范。',
    status: 'pass',
    timestamp: '2026-02-07 14:32:18',
  },
  {
    id: 'tc-002',
    screenshotUrl: 'https://picsum.photos/seed/test2/800/600',
    expectedResult: {
      type: 'text',
      description:
        '登录页面应包含以下元素：\n1. 顶部 Logo 居中显示，尺寸 120x40px\n2. 用户名输入框，placeholder 文本为「请输入用户名」\n3. 密码输入框，placeholder 文本为「请输入密码」\n4. 「记住我」复选框，默认未选中\n5. 蓝色登录按钮，宽度 100%，圆角 8px\n6. 底部「忘记密码？」链接，颜色 #0071e3',
    },
    aiAnalysis:
      '检测到 **2 个关键问题**：\n\n1. 「记住我」复选框 **缺失** — 在渲染结果中未找到该元素，DOM 树中不存在对应节点。\n2. 登录按钮的圆角为 **4px**，与预期的 8px 不符。\n\n其余元素均正常：Logo 尺寸正确（120x40px），输入框 placeholder 文本匹配，「忘记密码？」链接颜色为 #0071e3。',
    status: 'fail',
    timestamp: '2026-02-07 14:28:05',
  },
  {
    id: 'tc-003',
    screenshotUrl: 'https://picsum.photos/seed/test3/800/600',
    expectedResult: {
      type: 'image',
      imageUrl: 'https://picsum.photos/seed/expect3/800/600',
    },
    aiAnalysis:
      '商品列表页面渲染完全匹配预期。卡片网格布局为 4 列，间距 24px。每张卡片包含商品图片（16:9 比例）、标题（最多两行截断）、价格（红色 #ff3b30）和「加入购物车」按钮。页面底部分页组件显示正确，当前页码高亮。图片懒加载功能正常，可视区域外的图片使用占位符。',
    status: 'pass',
    timestamp: '2026-02-07 13:15:42',
  },
  {
    id: 'tc-004',
    screenshotUrl: 'https://picsum.photos/seed/test4/800/600',
    expectedResult: {
      type: 'text',
      description:
        '仪表盘页面应展示以下数据模块：\n- 顶部统计卡片：总用户数、活跃用户数、今日新增、收入总额\n- 中部折线图：过去 30 天的用户增长趋势\n- 右侧饼图：用户来源分布（直接访问、搜索引擎、社交媒体、推荐链接）\n- 底部表格：最近 10 条用户活动记录\n\n所有数字应使用千分位格式，货币前缀为 ¥',
    },
    aiAnalysis:
      '检测到 **3 个问题**：\n\n1. 收入总额卡片中的数字未使用千分位分隔符，显示为「1234567」而非「1,234,567」。\n2. 折线图的 Y 轴标签 **重叠**，在数据量较大时文字互相遮挡。\n3. 饼图中「推荐链接」的图例颜色与实际扇区颜色 **不一致**（图例为 #5856d6，扇区为 #af52de）。\n\n其余模块正常：统计卡片布局正确，表格数据渲染完整且排序功能可用。',
    status: 'fail',
    timestamp: '2026-02-07 12:08:33',
  },
  {
    id: 'tc-005',
    screenshotUrl: 'https://picsum.photos/seed/test5/800/600',
    expectedResult: {
      type: 'image',
      imageUrl: 'https://picsum.photos/seed/expect5/800/600',
    },
    aiAnalysis:
      '移动端响应式布局测试通过。在 375px 宽度下：导航栏折叠为汉堡菜单，内容区域单列布局，图片自适应宽度，底部导航栏固定显示 4 个图标。触摸区域最小尺寸为 44x44px，符合 Apple HIG 规范。所有文字大小在移动端可读，最小字号 14px。',
    status: 'pass',
    timestamp: '2026-02-07 11:45:19',
  },
  {
    id: 'tc-006',
    screenshotUrl: 'https://picsum.photos/seed/test6/800/600',
    expectedResult: {
      type: 'text',
      description:
        '设置页面应包含以下功能区块：\n- 个人信息区：头像（圆形裁剪）、昵称、邮箱\n- 通知设置：邮件通知开关、推送通知开关、周报订阅开关\n- 安全设置：修改密码入口、两步验证开关、登录设备管理\n- 数据管理：导出数据按钮、删除账户按钮（红色警示样式）\n\n所有开关默认状态应为「关闭」',
    },
    aiAnalysis:
      '页面结构完整，所有功能区块均已渲染。检测到 **1 个非关键问题**：\n\n1. 两步验证开关的默认状态为 **开启**，与预期的「关闭」不符。\n\n其余元素均符合预期：头像为圆形裁剪，邮件/推送/周报开关默认关闭，修改密码入口可点击，删除账户按钮使用红色 (#ff3b30) 警示样式。整体间距和排版与设计规范一致。',
    status: 'fail',
    timestamp: '2026-02-07 10:22:07',
  },
  {
    id: 'tc-007',
    screenshotUrl: 'https://picsum.photos/seed/test7/800/600',
    expectedResult: {
      type: 'image',
      imageUrl: 'https://picsum.photos/seed/expect7/800/600',
    },
    aiAnalysis:
      '搜索结果页面完全匹配预期设计。搜索框保持在顶部固定位置，输入内容「React hooks」正确显示。结果列表展示 10 条记录，每条包含标题（蓝色链接）、URL（绿色小字）和摘要（两行截断）。关键词在标题和摘要中以 **加粗** 形式高亮。筛选侧边栏显示正确，包含时间范围和内容类型筛选器。',
    status: 'pass',
    timestamp: '2026-02-07 09:58:44',
  },
  {
    id: 'tc-008',
    screenshotUrl: 'https://picsum.photos/seed/test8/800/600',
    expectedResult: {
      type: 'text',
      description:
        '订单详情页应显示：\n- 订单编号（格式：ORD-YYYYMMDD-XXXX）\n- 订单状态标签（待支付=橙色，已支付=蓝色，已发货=绿色，已完成=灰色）\n- 商品列表：商品图片、名称、规格、单价、数量、小计\n- 价格汇总：商品总价、运费、优惠金额、实付金额\n- 收货信息：姓名、电话（中间 4 位隐藏）、完整地址',
    },
    aiAnalysis:
      '订单详情页渲染正确，所有模块数据完整。订单编号格式符合规范（ORD-20260207-1234），状态标签颜色正确（当前状态「已发货」使用绿色）。商品列表项完整，价格计算准确。收货人电话正确脱敏显示（138****6789）。实付金额使用加粗红色显示，视觉层次清晰。',
    status: 'pass',
    timestamp: '2026-02-07 09:12:36',
  },
];
