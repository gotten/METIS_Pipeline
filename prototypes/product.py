from abc import ABC, abstractmethod

import cpl
from cpl.core import Msg

PIPELINE = r"METIS"


class PipelineProduct(ABC):
    """
        The abstract base class for a pipeline product:
        one FITS file with associated headers and a frame
    """

    tag: str = None
    group: cpl.ui.Frame.FrameGroup = None
    level: cpl.ui.Frame.FrameLevel = None
    frame_type: cpl.ui.Frame.FrameType = None

    def __init__(self,
                 recipe: 'MetisRecipeImpl',
                 header: cpl.core.PropertyList,
                 image: cpl.core.Image,
                 **kwargs):
        self.recipe: 'MetisRecipeImpl' = recipe
        self.header: cpl.core.PropertyList = header
        self.image: cpl.core.Image = image
        self.properties = cpl.core.PropertyList()

        # Raise NotImplemented in case a derived class forgot to set a class attribute
        if self.tag is None:
            raise NotImplementedError("Products must define 'tag'")

        if self.group is None:
            raise NotImplementedError("Products must define 'group'")

        if self.level is None:
            raise NotImplementedError("Products must define 'level'")

        if self.frame_type is None:
            raise NotImplementedError(f"Products must define 'frame_type'")

        if self.category is None:
            raise NotImplementedError(f"Products must define 'category'")

        self.add_properties()

    def add_properties(self):
        """
        Hook for adding properties.
        Currently only adds the ESO PRO CATG to every product,
        but derived classes are more than welcome to add their own stuff.
        """
        self.properties.append(
            cpl.core.Property(
                "ESO PRO CATG",         # Martin suspects this means ESO product category
                cpl.core.Type.STRING,
                self.category,
            )
        )

    def as_frame(self):
        """ Create a CPL Frame from this Product """
        return cpl.ui.Frame(
            file=self.output_file_name,
            tag=self.tag,
            group=self.group,
            level=self.level,
            frameType=self.frame_type,
        )

    def save(self):
        Msg.info(self.__class__.__qualname__, f"Saving product file as {self.output_file_name!r}.")
        cpl.dfs.save_image(
            self.recipe.frameset,       # All frames for the recipe
            self.recipe.parameters,     # The list of input parameters
            self.recipe.frameset,       # The list of raw and calibration frames actually used
                                        # (same as all frames, as we always use all the frames)
            self.image,                 # Image to be saved
            self.recipe.name,           # Name of the recipe
            self.properties,            # Properties to be appended
            PIPELINE,
            self.output_file_name,
            header=self.header,
        )

    @property
    @abstractmethod
    def category(self) -> str:
        """ Every product must define ESO PRO CATG """

    @property
    def output_file_name(self) -> str:
        """ Form the output file name (the detector part is variable) """
        return f"{self.category}.fits"


class DetectorProduct(PipelineProduct, metaclass=ABCMeta):
    def __init__(self,
                 recipe: 'MetisRecipe',
                 header: cpl.core.PropertyList,
                 image: cpl.core.Image,
                 *,
                 detector: str,
                 **kwargs):
        super().__init__(recipe, header, image, **kwargs)
        self.detector = detector
