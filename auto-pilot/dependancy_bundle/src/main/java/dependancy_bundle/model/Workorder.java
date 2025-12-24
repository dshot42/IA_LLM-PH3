package dependancy_bundle.model;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import dependancy_bundle.model.enumeration.WorkorderStatus;

import java.time.OffsetDateTime;

@Getter
@Setter
@Entity
@Table(
        name = "workorder"
)
public class Workorder {

    // =========================
    // Primary Key
    // =========================
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // =========================
    // Business Identifier
    // =========================
    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(
            name = "production_scenario_id",
            referencedColumnName = "id"
    )
    private ProductionScenario productionScenarioStep;


    // =========================
    // Status
    // =========================
    @Column(name = "status", nullable = false)
    private String status = WorkorderStatus.WAIT.name();

    // gestion par piece on compte les piece tout simplement
    // gestion par lot , on compte les lastStep pour incrementer les cycle du lot
    // on fonctionnera avec des handler en injection au cas par cas
    @Column(name = "nb_part_to_produce", nullable = true)
    private Long nbPartToProduce;

    @Column(name = "nb_part_finish", nullable = true)
    private Long nbPartFinish = 0L;

    @Column(name = "nb_part_rejected", nullable = true)
    private Long nbPartRejected = 0L;

    @Column(name = "nb_part_scrapped", nullable = true)
    private Long nbPartScrapped = 0L;
    // =========================
    // Timestamps
    // =========================
    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @Column(name = "started_at")
    private OffsetDateTime startedAt;

    @Column(name = "finished_at")
    private OffsetDateTime finishedAt;



}
