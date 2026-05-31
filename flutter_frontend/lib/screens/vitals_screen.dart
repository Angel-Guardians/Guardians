import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';

class _VitalSpec {
  const _VitalSpec(this.kind, this.label, this.unit, this.color, this.icon);
  final String kind;
  final String label;
  final String unit;
  final Color color;
  final IconData icon;
}

const _specs = [
  _VitalSpec('hr', 'Heart rate', 'bpm', AppTheme.danger, Icons.favorite_rounded),
  _VitalSpec('spo2', 'Blood oxygen', '%', AppTheme.good, Icons.bloodtype_rounded),
  _VitalSpec('bp', 'Blood pressure', 'mmHg', AppTheme.seed, Icons.monitor_heart_rounded),
  _VitalSpec('steps', 'Steps', '', Color(0xFF8B5CF6), Icons.directions_walk_rounded),
  _VitalSpec('calories', 'Calories', 'kcal', Color(0xFFEA8C2E), Icons.local_fire_department_rounded),
];

class VitalsScreen extends StatefulWidget {
  const VitalsScreen({super.key});

  @override
  State<VitalsScreen> createState() => _VitalsScreenState();
}

class _VitalsScreenState extends State<VitalsScreen> {
  final Map<String, VitalSeries?> _series = {};
  bool _loading = true;
  int _loadedForPatient = -1;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final state = Provider.of<AppState>(context);
    if (state.backendOnline && state.activePatientId != _loadedForPatient) {
      _loadedForPatient = state.activePatientId;
      _load(state);
    }
  }

  Future<void> _load(AppState state) async {
    setState(() => _loading = true);
    for (final spec in _specs) {
      try {
        _series[spec.kind] =
            await state.api.getVitals(spec.kind, patientId: state.activePatientId);
      } catch (_) {
        _series[spec.kind] = null;
      }
      if (mounted) setState(() {});
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (!state.backendOnline) {
      return InfoState(
        icon: Icons.cloud_off,
        title: 'Backend offline',
        message: 'Connect to the backend to see vitals.',
        color: AppTheme.danger,
        onRetry: () => state.refreshAll(),
      );
    }
    return RefreshIndicator(
      onRefresh: () => _load(state),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          Text('Last 24 hours',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text('Streamed live from the wearable.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant)),
          const SizedBox(height: 16),
          for (final spec in _specs) ...[
            _VitalChartCard(spec: spec, series: _series[spec.kind]),
            const SizedBox(height: 14),
          ],
          if (_loading)
            const Center(child: Padding(
              padding: EdgeInsets.all(8),
              child: CircularProgressIndicator())),
        ],
      ),
    );
  }
}

class _VitalChartCard extends StatelessWidget {
  const _VitalChartCard({required this.spec, required this.series});

  final _VitalSpec spec;
  final VitalSeries? series;

  bool get _isBp => spec.kind == 'bp';

  @override
  Widget build(BuildContext context) {
    final points = series?.points ?? [];
    final hasData = points.isNotEmpty;

    String latestLabel = '—';
    if (hasData) {
      final last = points.last;
      if (_isBp) {
        latestLabel =
            '${(last.systolic ?? last.value).toStringAsFixed(0)}/${(last.diastolic ?? 0).toStringAsFixed(0)}';
      } else {
        latestLabel = last.value.toStringAsFixed(spec.kind == 'spo2' ? 0 : 0);
      }
    }

    return SectionCard(
      icon: spec.icon,
      iconColor: spec.color,
      title: spec.label,
      subtitle: hasData ? '${points.length} readings' : 'Awaiting data',
      trailing: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(latestLabel,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800, color: spec.color)),
          if (spec.unit.isNotEmpty)
            Text(spec.unit,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
        ],
      ),
      child: SizedBox(
        height: 150,
        child: hasData
            ? _buildChart(context, points)
            : Center(
                child: Text('Data will appear once the wearable streams.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color:
                            Theme.of(context).colorScheme.onSurfaceVariant)),
              ),
      ),
    );
  }

  Widget _buildChart(BuildContext context, List<VitalPoint> points) {
    final theme = Theme.of(context);
    final minX = 0.0;
    final maxX = (points.length - 1).toDouble();

    List<FlSpot> spots(double Function(VitalPoint) sel) => [
          for (var i = 0; i < points.length; i++)
            FlSpot(i.toDouble(), sel(points[i])),
        ];

    final lines = <LineChartBarData>[];
    if (_isBp) {
      lines.add(_lineData(spots((p) => p.systolic ?? p.value), spec.color));
      lines.add(_lineData(
          spots((p) => p.diastolic ?? 0), spec.color.withOpacity(0.45)));
    } else {
      lines.add(_lineData(spots((p) => p.value), spec.color, fill: true));
    }

    return LineChart(
      LineChartData(
        minX: minX,
        maxX: maxX < 1 ? 1 : maxX,
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: null,
          getDrawingHorizontalLine: (v) => FlLine(
            color: theme.colorScheme.outlineVariant.withOpacity(0.4),
            strokeWidth: 1,
          ),
        ),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 38,
              getTitlesWidget: (v, meta) => Text(
                v.toStringAsFixed(0),
                style: theme.textTheme.bodySmall?.copyWith(fontSize: 10),
              ),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 22,
              interval: (maxX / 3).clamp(1, double.infinity),
              getTitlesWidget: (v, meta) {
                final i = v.round();
                if (i < 0 || i >= points.length) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    DateFormat('HH:mm').format(points[i].ts.toLocal()),
                    style: theme.textTheme.bodySmall?.copyWith(fontSize: 10),
                  ),
                );
              },
            ),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => theme.colorScheme.inverseSurface,
            getTooltipItems: (items) => items
                .map((it) => LineTooltipItem(
                      it.y.toStringAsFixed(0),
                      TextStyle(
                          color: theme.colorScheme.onInverseSurface,
                          fontWeight: FontWeight.w600),
                    ))
                .toList(),
          ),
        ),
        lineBarsData: lines,
      ),
    );
  }

  LineChartBarData _lineData(List<FlSpot> spots, Color color,
      {bool fill = false}) {
    return LineChartBarData(
      spots: spots,
      isCurved: true,
      curveSmoothness: 0.25,
      color: color,
      barWidth: 2.5,
      dotData: const FlDotData(show: false),
      belowBarData: fill
          ? BarAreaData(
              show: true,
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [color.withOpacity(0.22), color.withOpacity(0.0)],
              ),
            )
          : BarAreaData(show: false),
    );
  }
}
