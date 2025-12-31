package dependancy_bundle.dto;

public class SocketDto {

    public record MachineLiveDto(

            String machine_code,
            String machine_name,
            Integer nominal_duration_s,

            String last_ts,
            Long last_part_id,

            String last_level,
            String last_code,
            String last_message,

            Integer last_cycle,

            Long last_step_id,
            String last_step_name,

            Double last_duration,
            String state
    ) {
    }
}
