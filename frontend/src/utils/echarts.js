// ECharts 按需引入 — 仅导入项目使用的图表类型和组件
// 替代全量 import * as echarts from 'echarts'，减少 ~800KB 包体积
import * as echarts from 'echarts/core'
import { PieChart, LineChart, RadarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  PieChart,
  LineChart,
  RadarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
  CanvasRenderer,
])

export default echarts