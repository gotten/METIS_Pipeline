from typing import Dict, Any

import cpl
from cpl.core import Msg

from prototypes.product import PipelineProduct
from prototypes.rawimage import RawImageProcessor


class MetisBaseImgFlatImpl(RawImageProcessor):
    class Input(RawImageProcessor.Input):
        """
        Base class for Inputs which create flats. Requires a bunch of raw frames and a master dark.
        """
        tag_raw = None
        tags_dark = None

        def __init__(self, frameset: cpl.ui.FrameSet):
            self.master_dark: cpl.ui.Frame | None = None
            super().__init__(frameset)

        def categorize_frame(self, frame: cpl.ui.Frame) -> None:
            match frame.tag:
                case self.tag_raw:
                    frame.group = cpl.ui.Frame.FrameGroup.RAW
                    self.raw.append(frame)
                    Msg.debug(self.__class__.__qualname__, f"Got raw frame: {frame.file}.")
                case tag if tag in self.tags_dark:
                    frame.group = cpl.ui.Frame.FrameGroup.CALIB
                    self.master_dark = frame
                    Msg.debug(self.__class__.__qualname__, f"Got master dark frame: {frame.file}.")
                case _:
                    super().categorize_frame(frame)

        def verify(self) -> None:
            # First verify the raw frames (provided by base class)
            super().verify()

            print(self.master_dark)
            if self.master_dark is None:
                raise cpl.core.DataNotFoundError("No masterdark frames found in the frameset.")

    class Product(PipelineProduct):
        group = cpl.ui.Frame.FrameGroup.PRODUCT
        level = cpl.ui.Frame.FrameLevel.FINAL
        frame_type = cpl.ui.Frame.FrameType.IMAGE

        band: str = None

        @property
        def category(self) -> str:
            return fr"MASTER_IMG_FLAT_LAMP_{self.band}"

        @property
        def output_file_name(self) -> str:
            return fr"MASTER_IMG_FLAT_LAMP_{self.band}.fits"

        @property
        def tag(self) -> str:
            return self.category

    # Subtract the dark from every raw image
    def process_images(self) -> Dict[str, PipelineProduct]:
        # TODO: Detect detector
        # TODO: Twilight

        # By default, images are loaded as Python float data. Raw image
        # data which is usually represented as 2-byte integer data in a
        # FITS file is converted on the fly when an image is loaded from
        # a file. It is however also possible to load images without
        # performing this conversion.

        raw_images = self.load_input_images()
        master_dark = cpl.core.Image.load(self.input.master_dark.file, extension=0)

        for raw_image in raw_images:
            Msg.debug(self.__class__.__qualname__, f"Subtracting image {raw_image}")
            raw_image.subtract(master_dark)

        # Combine the images in the image list using the image stacking option requested by the user.
        method = self.parameters[f"{self.name}.stacking.method"].value
        Msg.info(self.name, f"Combining images using method {method!r}")

        # TODO: preprocessing steps like persistence correction / nonlinearity (or not) should come here

        raw_images = self.load_input_images()
        combined_image = None

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
                Msg.error(
                    self.__class__.__qualname__,
                    f"Got unknown stacking method {method!r}. Stopping right here!",
                )

        header = cpl.core.PropertyList.load(self.input.raw[0].file, 0)

        self.products = {
            self.name.upper():
                self.Product(self, header, combined_image,
                             file_name=f"MASTER_IMG_FLAT_LAMP_LM.fits"),
        }
        return self.products