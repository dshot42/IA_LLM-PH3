package simulator;


import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
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
            (ts, part_id, workorder_id, machine, level, code, message, cycle, step_id, step_name, duration, payload)
            VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)
            """;

    public void insertEvent(
            OffsetDateTime ts,
            Long partId,
            String machine,
            String level,
            String code,
            String message,
            Integer cycle,
            Long productionStepId,
            BigDecimal duration,
            JsonNode payload,
            Long workorderId
    ) {
        try {
            jdbc.update(
                    INSERT_SQL,
                    ts,
                    partId,
                    getMachineId(machine),
                    level,
                    code,
                    message,
                    cycle,
                    productionStepId,
                    duration,
                    payload == null ? null : payload.toString(),
                    workorderId
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

    public Long insertPart(String externalPartId) {
        System.out.println("Inserting part with id " + externalPartId);
        return jdbc.queryForObject("""
                    INSERT INTO part (external_part_id, line_id, status)
                    VALUES (?, ?, ?)
                    ON CONFLICT (external_part_id)
                    DO UPDATE SET external_part_id = EXCLUDED.external_part_id
                    RETURNING id
                """, Long.class, externalPartId, 1, "IN_PROGRESS");
    }

    public Long getMachineId(String name) {
        return jdbc.queryForObject(
                "SELECT id FROM machine WHERE code = ?",
                Long.class,
                name
        );

    }
}
