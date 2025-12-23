package supervision.industrial.auto_pilot.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import supervision.industrial.auto_pilot.dto.AnomalyDetectionDto;
import org.springframework.stereotype.Service;

@Service
public class AnomalyDetectionService {



    private final ObjectMapper mapper = new ObjectMapper();

    public AnomalyDetectionDto detectMachineTimeOverrun(
            double cycleDuration,
            double nominalMax
    ) {
        if (cycleDuration > nominalMax) {
            ArrayNode reasons = mapper.createArrayNode();
            reasons.add("machine_time_overrun");

            return new AnomalyDetectionDto(
                    true,
                    cycleDuration,
                    cycleDuration - nominalMax,
                    reasons,
                    "SERIOUS"
            );
        }

        return new AnomalyDetectionDto(
                false,
                cycleDuration,
                null,
                null,
                "INFO"
        );
    }
}
