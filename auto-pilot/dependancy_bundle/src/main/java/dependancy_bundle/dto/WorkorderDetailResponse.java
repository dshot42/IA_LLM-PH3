package supervision.industrial.auto_pilot.api.dto;

import dependancy_bundle.model.PlcAnomaly;
import dependancy_bundle.model.PlcEvent;

import java.util.List;

public class WorkorderDetailResponse {
    private String workorderId;
    private List<PlcEvent> events;
    private List<PlcAnomaly> anomalies;

    public WorkorderDetailResponse() {}

    public WorkorderDetailResponse(String workorderId, List<PlcEvent> events, List<PlcAnomaly> anomalies) {
        this.workorderId = workorderId;
        this.events = events;
        this.anomalies = anomalies;
    }

    public String getWorkorderId() { return workorderId; }
    public void setWorkorderId(String workorderId) { this.workorderId = workorderId; }

    public List<PlcEvent> getEvents() { return events; }
    public void setEvents(List<PlcEvent> events) { this.events = events; }

    public List<PlcAnomaly> getAnomalies() { return anomalies; }
    public void setAnomalies(List<PlcAnomaly> anomalies) { this.anomalies = anomalies; }
}
