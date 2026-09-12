from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

from treeforge.android.extraction.source.stage import (
    SourceArtifactMaterializationStage,
)
from treeforge.android.extraction.partition.stage import (
    PartitionImageExtractionStage,
)
from treeforge.android.extraction.recursive.materializer import (
    ApexArtifactMaterializer,
    AvbArtifactMaterializer,
    BootArtifactMaterializer,
    ConcatenatedFdtArtifactMaterializer,
    CpioArtifactMaterializer,
    EmbeddedElfArtifactMaterializer,
    DtboArtifactMaterializer,
    Ext4StructureMaterializer,
    FbpkArtifactMaterializer,
    UfpkArtifactMaterializer,
    BootFirmwareEnvelopeMaterializer,
    SflbArtifactMaterializer,
    SflbCompressedResourceMaterializer,
    FilesystemArtifactMaterializer,
    KernelArtifactMaterializer,
    LiblpStructureMaterializer,
    LogicalPartitionContainerMaterializer,
    RamdiskArtifactMaterializer,
    SparseArtifactMaterializer,
    StandaloneAvbVbmetaMaterializer,
)
from treeforge.android.extraction.recursive.stage import (
    RecursiveExtractionStage,
)
from treeforge.android.extraction.partition.extractor import (
    LogicalPartitionExtractor,
)
from treeforge.android.extraction.partition.lpunpack import (
    LpunpackRunner,
)
from treeforge.android.extraction.partition.lpdump import (
    LpdumpRunner,
)
from treeforge.android.extraction.partition.super_metadata_inspector import (
    SuperMetadataInspector,
)
from treeforge.android.extraction.sparse.extractor import (
    SparseConverter,
    SparseImageExtractor,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.pipeline.pipeline import (
    Pipeline,
)
from treeforge.core.pipeline.stage import (
    PipelineStage,
)
from treeforge.core.progress import ProgressCallback


if TYPE_CHECKING:
    from treeforge.android.partition.inventory_resolver import (
        PartitionInventoryResolver,
    )


class ExtractionPipelineLike(
    Protocol,
):
    """
    Pipeline contract retained for injected pipeline collaborators.
    """

    def add_stage(
        self,
        stage: PipelineStage,
    ) -> None:
        ...

    def run(
        self,
        context: Context,
    ) -> None:
        ...


class AndroidExtractionPipeline:
    """
    Canonical Android physical Extraction subsystem.

    Canonical factory-image ordering spans the Partition Layout boundary:

        Discovery
            ↓
        source-artifact materialization
            ↓
        Partition Layout
            ↓
        partition-image Extraction
            ↓
        recursive artifact expansion
            ├── sparse normalization
            ├── boot-family component extraction
            ├── kernel decompression
            ├── ramdisk decompression
            ├── CPIO extraction
            ├── embedded ELF extraction
            ├── APEX extraction
            ├── DTBO entry extraction
            ├── logical-partition container expansion
            └── filesystem extraction
            ↓
        canonical PartitionInventory projection

    Extraction remains the sole owner of all physical materialization,
    transformation, and directly-accessible partition projection.

    Partition Layout consumes canonical Extraction output but does not own
    materialization.

    This subsystem stops before filesystem metadata.
    """

    name = "Android Extraction"

    def __init__(
        self,
        *,
        host_tools: (
            AndroidHostTools
            | None
        ) = None,
        pipeline: (
            ExtractionPipelineLike
            | None
        ) = None,
        source_materialization_stage: (
            PipelineStage
            | None
        ) = None,
        partition_extraction_stage: (
            PipelineStage
            | None
        ) = None,
        recursive_extraction_stage: (
            PipelineStage
            | None
        ) = None,
        partition_inventory_resolver: (
            PartitionInventoryResolver
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.host_tools = (
            host_tools
            if host_tools is not None
            else AndroidHostTools()
        )

        #
        # Retained for the existing public constructor contract.
        #
        # The Extraction subsystem can no longer register all three physical
        # stages into one uninterrupted Pipeline because Partition Layout
        # legitimately consumes canonical source materialization between the
        # first and second Extraction operations.
        #
        self.pipeline = (
            pipeline
            if pipeline is not None
            else Pipeline()
        )

        self.source_materialization_stage = (
            source_materialization_stage
            if source_materialization_stage
            is not None
            else SourceArtifactMaterializationStage(
                progress_callback=progress_callback,
            )
        )

        self.partition_extraction_stage = (
            partition_extraction_stage
            if partition_extraction_stage
            is not None
            else PartitionImageExtractionStage(
                logical_extractor=(
                    LogicalPartitionExtractor(
                        runner=(
                            LpunpackRunner(
                                executable=(
                                    self.host_tools.lpunpack
                                ),
                            )
                        )
                    )
                ),
                progress_callback=progress_callback,
            )
        )

        if partition_inventory_resolver is None:
            from treeforge.android.partition.inventory_resolver import (
                PartitionInventoryResolver,
            )

            partition_inventory_resolver = (
                PartitionInventoryResolver()
            )

        self.partition_inventory_resolver = (
            partition_inventory_resolver
        )

        self.recursive_extraction_stage = (
            recursive_extraction_stage
            if recursive_extraction_stage
            is not None
            else RecursiveExtractionStage(
                materializers=(
                    SparseArtifactMaterializer(
                        extractor=(
                            SparseImageExtractor(
                                converter=SparseConverter(
                                    executable=(
                                        self.host_tools.simg2img
                                    ),
                                )
                            )
                        ),
                    ),
                    BootArtifactMaterializer(),
                    ConcatenatedFdtArtifactMaterializer(),
                    DtboArtifactMaterializer(),
                    StandaloneAvbVbmetaMaterializer(),
                    Ext4StructureMaterializer(),
                    AvbArtifactMaterializer(),
                    KernelArtifactMaterializer(),
                    RamdiskArtifactMaterializer(),
                    CpioArtifactMaterializer(),
                    ApexArtifactMaterializer(),
                    FbpkArtifactMaterializer(),
                    UfpkArtifactMaterializer(),
                    BootFirmwareEnvelopeMaterializer(),
                    SflbArtifactMaterializer(),
                    SflbCompressedResourceMaterializer(),
                EmbeddedElfArtifactMaterializer(),
                    LiblpStructureMaterializer(),
                    LogicalPartitionContainerMaterializer(
                        extractor=(
                            LogicalPartitionExtractor(
                                runner=(
                                    LpunpackRunner(
                                        executable=(
                                            self.host_tools.lpunpack
                                        ),
                                    )
                                ),
                            )
                        ),
                        inspector=(
                            SuperMetadataInspector(
                                runner=(
                                    LpdumpRunner(
                                        executable=(
                                            self.host_tools.lpdump
                                        ),
                                    )
                                ),
                            )
                        ),
                    ),
                    FilesystemArtifactMaterializer(),
                ),
                progress_callback=progress_callback,
            )
        )

    def materialize_sources(
        self,
        context: Context,
    ) -> None:
        """
        Establish canonical physical accessibility for Discovery artifacts.

        This is the pre-Partition-Layout portion of the single Extraction
        subsystem.

        It performs no partition interpretation.
        """

        self._validate_context(
            context
        )

        self.source_materialization_stage.execute(
            context
        )

    def continue_after_layout(
        self,
        context: Context,
    ) -> None:
        """
        Continue canonical Extraction after Partition Layout is established.
        """

        self._validate_context(
            context
        )

        if context.partition_layout is None:
            raise RuntimeError(
                "Partition Layout must be established before "
                "post-layout Extraction"
            )

        self.partition_extraction_stage.execute(
            context
        )

        self.recursive_extraction_stage.execute(
            context
        )

        extraction = (
            context.android_extraction
        )

        if extraction is None:
            raise RuntimeError(
                "Canonical Extraction state is missing after "
                "recursive physical expansion"
            )

        try:
            inventory = (
                self.partition_inventory_resolver
                .resolve(
                    context.partition_layout,
                    extraction,
                )
            )
        except Exception as error:
            raise RuntimeError(
                "Unable to project canonical PartitionInventory "
                "from completed Extraction state: "
                f"{error}"
            ) from error

        from treeforge.android.partition.inventory import (
            PartitionInventory,
        )

        if not isinstance(
            inventory,
            PartitionInventory,
        ):
            raise RuntimeError(
                "Partition inventory resolver returned "
                "an invalid result"
            )

        context.partition_inventory = (
            inventory
        )

    def execute(
        self,
        context: Context,
    ) -> None:
        """
        Execute the established post-Layout Extraction contract.

        Factory-image orchestration with a not-yet-established Partition
        Layout must instead use:

            materialize_sources()
                ↓
            Partition Layout
                ↓
            continue_after_layout()
        """

        self.run(
            context
        )

    def run(
        self,
        context: Context,
    ) -> None:
        """
        Run complete Extraction when Partition Layout already exists.

        This preserves the existing post-Layout caller contract.

        New factory-image orchestration must establish the inter-stage
        Partition Layout boundary explicitly.
        """

        self._validate_context(
            context
        )

        if context.partition_layout is None:
            raise RuntimeError(
                "AndroidExtractionPipeline.run requires an established "
                "Partition Layout; factory-image orchestration must call "
                "materialize_sources(), establish Partition Layout, then "
                "continue_after_layout()"
            )

        self.materialize_sources(
            context
        )

        self.continue_after_layout(
            context
        )

    @staticmethod
    def _validate_context(
        context: Context,
    ) -> None:
        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )
