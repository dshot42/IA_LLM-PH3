package simulator;


import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;

@Repository
public class PlcEventDao {

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;

    public PlcEventDao(JdbcTemplate jdbc, ObjectMapper om) {
        this.jdbc = jdbc;
        this.om = om;
    }

    private static final String INSERT_SQL = """
        INSERT INTO plc_events
        (ts, part_id, machine, level, code, message, cycle, step_id, step_name, duration, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)
        """;

    public void insertEvent(
            OffsetDateTime ts,
            String partId,
            String machine,
            String level,
            String code,
            String message,
            int cycle,
            String stepId,
            String stepName,
            Double duration,
            Object payloadObj
    ) {
        try {
            String payloadJson = payloadObj == null ? null : om.writeValueAsString(payloadObj);
            jdbc.update(
                    INSERT_SQL,
                    ts, partId, machine, level, code, message,
                    cycle, stepId, stepName, duration, payloadJson
            );
        } catch (Exception e) {
            throw new RuntimeException("Failed to insert plc_event", e);
        }
    }

    public void clearTables() {
        jdbc.update("DELETE FROM part");
        jdbc.update("DELETE FROM plc_events");
        jdbc.update("DELETE FROM plc_anomalies");
    }

    public void insertPart(String externalPartId) {
        System.out.println("Inserting part with id " + externalPartId);
        jdbc.update("""
            INSERT INTO part (external_part_id, line_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT (external_part_id) DO NOTHING
        """, externalPartId, 1, "IN_PROGRESS");
    }
}
