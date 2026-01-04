package supervision.industrial.auto_pilot.api.dto;

    public record ReccurenceAnomalyAnalyseDto(
            int windowDays,

            long totalOccurrences,

            double meanIntervalS,
            double stdDevIntervalS,

            double meanOverrunS,
            double stdDevOverrunS,

            boolean frequencyIncreasing,
            boolean overrunIncreasing,

            String trendConclusion // "STABLE", "EN AUGMENTATION", "AGGRAVATION"
    ) {}
