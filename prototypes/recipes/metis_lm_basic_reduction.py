from typing import Any, Dict
from schema import Schema

import cpl
from cpl.core import Msg

from prototypes.base import MetisRecipeImpl, MetisRecipe
from prototypes.product import PipelineProduct
from prototypes.rawimage import RawImageProcessor


class MetisLmBasicReductionImpl(RawImageProcessor):
    class Input(RawImageProcessor.Input):
        bias: cpl.ui.Frame
        flat: cpl.ui.Frame

        def categorize_frame(self, frame):
            if frame.tag == "LM_IMAGE_SCI_RAW":
                frame.group = cpl.ui.Frame.FrameGroup.RAW
                self.raw.append(frame)
                Msg.debug(self.__class__.__name__, f"Got raw frame: {frame.file}.")
            elif frame.tag == "MASTER_DARK_2RG":
                frame.group = cpl.ui.Frame.FrameGroup.CALIB
                self.master_dark = frame
                Msg.debug(self.__class__.__name__, f"Got bias frame: {frame.file}.")
            elif frame.tag == "MASTER_GAIN_2RG":
                frame.group = cpl.ui.Frame.FrameGroup.CALIB
                self.master_gain = frame
                Msg.debug(self.__class__.__name__, f"Got bias frame: {frame.file}.")
            elif frame.tag == "MASTER_IMG_FLAT_LAMP_LM":
                frame.group = cpl.ui.Frame.FrameGroup.CALIB
                self.master_flat = frame
                Msg.debug(self.__class__.__name__, f"Got bias frame: {frame.file}.")
            elif frame.tag == "MASTER_FLAT_LAMP":
                frame.group = cpl.ui.Frame.FrameGroup.CALIB
                self.master_flat = frame
                Msg.debug(self.__class__.__name__, f"Got flat field frame: {frame.file}.")
            else:
                super().categorize_frame(frame)

        def verify(self):
            super().verify()
            #import pdb; pdb.set_trace()
            
            try:
                self.bias = cpl.core.Image.load(self.master_dark.file, extension=0)
                Msg.info(self.__class__.__name__, f"Loaded bias frame {self.master_dark.file!r}.")
            except:
                raise cpl.core.DataNotFoundError("No bias frame in frameset.")

            try:
                self.flat = cpl.core.Image.load(self.master_flat.file, extension=0)
                Msg.info(self.__class__.__name__, f"Loaded flat frame {self.master_flat.file!r}.")
            except:
                raise cpl.core.DataNotFoundError("No flat frame in frameset.")

    class Product(PipelineProduct):
        tag: str = "OBJECT_REDUCED"
        group = cpl.ui.Frame.FrameGroup.PRODUCT
        level = cpl.ui.Frame.FrameLevel.FINAL
        frame_type = cpl.ui.Frame.FrameType.IMAGE

        @property
        def category(self) -> str:
            return self.tag

        @property
        def output_file_name(self):
            return f"{self.category}.fits"
        

    def verify_input_frames(self) -> None:
        """ RawImageProcessor mixin wants to see a bunch of raw frames. """
        pass

    
    def process_images(self) -> Dict[str, PipelineProduct]:
        method = self.parameters["basic_reduction.stacking.method"].value
        Msg.info(self.__class__.__name__, f"Combining images using method {method!r}")
        #import pdb; pdb.set_trace()
        Msg.info(self.__class__.__name__, f"Starting processing image attibute.")
        raw_images = self.load_input_images()
        match method:
            case "add":
                for idx, image in enumerate(raw_images):
                    if idx == 0:
                        combined_image = image
                    else:
                        combined_image.add(image)
            case "average":
                combined_image = raw_images.collapse_create()
            case "median":
                combined_image = raw_images.collapse_median_create()
            case _:
                Msg.error(self.__class__.__name__,
                          f"Got unknown stacking method {method!r}. Stopping right here!")

        header = cpl.core.PropertyList.load(self.input.raw[0].file, 0)

        self.products = {
            fr'OBJECT_REDUCED_{self.detector_name}':
                self.Product(self, header, combined_image,
                             detector_name=self.detector_name),
        }

        return self.products
    @property
    def detector_name(self) -> str:
        return "2RG"


class MetisLmBasicReduction(MetisRecipe):
    # Fill in recipe information
    _name = "metis_lm_basic_reduction"
    _version = "0.1"
    _author = "Chi-Hung Yan"
    _email = "chyan@asiaa.sinica.edu.tw"
    _copyright = "GPL-3.0-or-later"
    _synopsis = "Basic science image data processing"
    _description = (
        "The recipe combines all science input files in the input set-of-frames using\n"
        + "the given method. For each input science image the master bias is subtracted,\n"
        + "and it is divided by the master flat."
    )

    parameters = cpl.ui.ParameterList([
        cpl.ui.ParameterEnum(
            name="basic_reduction.stacking.method",
            context="basic_reduction",
            description="Name of the method used to combine the input images",
            default="add",
            alternatives=("add", "average", "median"),
        )
    ])
    implementation_class = MetisLmBasicReductionImpl
"""

    def __init__(self) -> None:
        super().__init__()
        self.implementation = self.implementation_class(self)

    def run(self, frameset: cpl.ui.FrameSet, settings: Dict[str, Any]) -> cpl.ui.FrameSet:
        raw_frames = cpl.ui.FrameSet()
        product_frames = cpl.ui.FrameSet()
        bias_frame = None
        flat_frame = None

        output_file = "OBJECT_REDUCED.fits"

        #import pdb; pdb.set_trace()

        # Flat field preparation: subtract bias and normalize it to median 1
        Msg.info(self.__class__.__name__, "Preparing flat field")
        if self.flat_image:
            if self.bias_image:
                self.flat_image.subtract(self.bias_image)
            median = self.flat_image.get_median()
            self.flat_image.divide_scalar(median)

        header = None
        processed_images = cpl.core.ImageList()
        for idx, frame in enumerate(raw_frames):
            Msg.info(self.__class__.__name__, f"Processing {frame.file!r}...")

            if idx == 0:
                header = cpl.core.PropertyList.load(frame.file, 0)

            Msg.debug(self.__class__.__name__, "Loading image.")
            raw_image = cpl.core.Image.load(frame.file, extension=1)

            if self.bias_image:
                Msg.debug(self.__class__.__name__, "Bias subtracting...")
                raw_image.subtract(self.bias_image)

            if self.flat_image:
                Msg.debug(self.__class__.__name__, "Flat fielding...")
                raw_image.divide(self.flat_image)

            # Insert the processed image in an image list. Of course
            # there is also an append() method available.
            processed_images.insert(idx, raw_image)

        # Combine the images in the image list using the image stacking
        # option requested by the user.
        method = self.parameters["basic_reduction.stacking.method"].value
        Msg.info(self.__class__.__name__, f"Combining images using method {method!r}")

        combined_image = None
        if method == "add":
            for idx, image in enumerate(processed_images):
                if idx == 0:
                    combined_image = image
                else:
                    combined_image.add(image)
        elif method == "average":
            combined_image = processed_images.collapse_create()
        elif method == "median":
            combined_image = processed_images.collapse_median_create()
        else:
            Msg.error(
                self.__class__.__name__,
                f"Got unknown stacking method {method!r}. Stopping right here!",
            )
            # Since we did not create a product we need to return an empty
            # ui.FrameSet object. The result frameset product_frames will do,
            # it is still empty here!
            return product_frames

        return product_frames
"""