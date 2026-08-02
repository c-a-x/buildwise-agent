<script setup lang="ts">
import type { ReportStatistics } from '@/types/report'

defineProps<{ statistics: ReportStatistics }>()
</script>

<template><div class="report-metrics"><div class="report-metric"><strong>{{ statistics.incident_total }}</strong><small>今日隐患</small></div><div class="report-metric"><strong>{{ statistics.high_risk_total }}</strong><small>高风险及以上</small></div><div class="report-metric"><strong>{{ statistics.new_work_orders }}</strong><small>新建工单</small></div><div class="report-metric"><strong>{{ statistics.closed_work_orders }}</strong><small>今日关闭</small></div></div></template>
