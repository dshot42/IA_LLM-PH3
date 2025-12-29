package supervision.industrial.auto_pilot.api.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;

import java.util.List;

public abstract  class SkipPLCEvent {

        @JsonIgnore
        abstract List<?> getPlcEvents();
    }
