package supervision.industrial.auto_pilot.dto;

import supervision.industrial.auto_pilot.model.PlcAnomaly;
import supervision.industrial.auto_pilot.model.PlcEvent;

import java.util.List;

public class PartDetailResponse {
    private String partId;
    private List<PlcEvent> events;
    private List<PlcAnomaly> anomalies;

    public PartDetailResponse() {}

    public PartDetailResponse(String partId, List<PlcEvent> events, List<PlcAnomaly> anomalies) {
        this.partId = partId;
        this.events = events;
        this.anomalies = anomalies;
    }

    public String getPartId() { return partId; }
    public void setPartId(String partId) { this.partId = partId; }

    public List<PlcEvent> getEvents() { return events; }
    public void setEvents(List<PlcEvent> events) { this.events = events; }

    public List<PlcAnomaly> getAnomalies() { return anomalies; }
    public void setAnomalies(List<PlcAnomaly> anomalies) { this.anomalies = anomalies; }
}
