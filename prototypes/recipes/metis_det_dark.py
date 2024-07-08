import cpl
from cpl.core import Msg
from typing import Dict, Any

from prototypes.base import MetisRecipeImpl
from prototypes.product import PipelineProduct


class MetisDetDarkImpl(MetisRecipeImpl):
    class Product(PipelineProduct):
        def __init__(self, recipe, header, frame, *, detector_name, **kwargs):
            self.detector_name = detector_name
            super().__init__(recipe, header, frame, **kwargs)

        def create_frame(self):
            return cpl.ui.Frame(file=self.output_file_name,
                                tag=rf"MASTER_DARK_{self.detector_name}",
                                group=cpl.ui.Frame.FrameGroup.PRODUCT,
                                level=cpl.ui.Frame.FrameLevel.FINAL,
                                frameType=cpl.ui.Frame.FrameType.IMAGE)

        @property
        def category(self) -> str:
            return rf"MASTER_DARK_{self.detector_name}"

        @property
        def output_file_name(self) -> str:
            """ Form the output file name (the detector part is variable here) """
            return rf"MASTER_DARK_{self.detector_name}.fits"

    def __init__(self, recipe):
        super().__init__(recipe)
        self._detector_name = None

    def categorize_frameset(self) -> cpl.ui.FrameSet:
        """
        Go through the list of input frames, check their tags and filter out suitable files.
        """

        for frame in self.frameset:
            # TODO: N and GEO
            match frame.tag:
                case x if x in ["DARK_LM_RAW", "DARK_N_RAW", "DARK_IFU_RAW"]:
                    frame.group = cpl.ui.Frame.FrameGroup.RAW
                    self.input_frames.append(frame)
                    Msg.debug(self.name, f"Got raw frame: {frame.file}.")
                case _:
                    Msg.warning(self.name,
                                f"Got frame {frame.file!r} with unexpected tag {frame.tag!r}, ignoring.")

        return self.input_frames

    def verify_input(self) -> None:
        if len(self.input_frames) == 0:
            raise cpl.core.DataNotFoundError("No raw frames in frameset.")

        detectors = []

        for idx, frame in enumerate(self.input_frames):
            header = cpl.core.PropertyList.load(frame.file, 0)
            raw_image = cpl.core.Image.load(frame.file, extension=1)
            det = header['ESO DPR TECH'].value
            try:
                detector_name = {
                    'IMAGE,LM': '2RG',
                    'IMAGE,N': 'GEO',
                    'IFU': 'IFU'
                }[det]
            except KeyError as e:
                raise KeyError(f"Invalid detector name! In {frame.file}, ESO DPR TECH is '{det}'") from e

            detectors.append(detector_name)

        # Check if all the raws have the same detector, if not, we have a problem
        if len(set(detectors)) == 1:
            self._detector_name = detectors[0]
        else:
            raise ValueError(f"Darks from more than one detector found: {set(detectors)}!")

    def process_images(self) -> Dict[str, PipelineProduct]:
        # By default, images are loaded as Python float data. Raw image
        # data which is usually represented as 2-byte integer data in a
        # FITS file is converted on the fly when an image is loaded from
        # a file. It is however also possible to load images without
        # performing this conversion.

        # Flat field preparation: subtract bias and normalize it to median 1
        # Msg.info(self.name, "Preparing flat field")
        # if flat_image:
        #     if bias_image:
        #         flat_image.subtract(bias_image)
        #     median = flat_image.get_median()
        #     flat_image.divide_scalar(median)

        # Combine the images in the image list using the image stacking
        # option requested by the user.
        method = self.parameters["metis_det_dark.stacking.method"].value
        Msg.info(self.name, f"Combining images using method {method!r}")

        # TODO: preprocessing steps like persistence correction / nonlinearity (or not)
        processed_images = self.input_images
        combined_image = None

        match method:
            case "add":
                for idx, image in enumerate(processed_images):
                    if idx == 0:
                        combined_image = image
                    else:
                        combined_image.add(image)
            case "average":
                combined_image = processed_images.collapse_create()
            case "median":
                combined_image = processed_images.collapse_median_create()
            case _:
                Msg.error(self.name, f"Got unknown stacking method {method!r}. Stopping right here!")

        header = cpl.core.PropertyList.load(self.input_frames[0].file, 0)

        self.products = {
            f'METIS_{self.detector_name}_DARK':
                self.Product(self,
                             header, combined_image,
                             detector_name=self.detector_name,
                             file_name=f"MASTER_DARK_{self.detector_name}.fits"),
        }

        return self.products

    @property
    def detector_name(self) -> str:
        return self._detector_name


class MetisDetDark(cpl.ui.PyRecipe):
    # Fill in recipe information
    _name = "metis_det_dark"
    _version = "0.1"
    _author = "Kieran Chi-Hung Hugo Martin"
    _email = "hugo@buddelmeijer.nl"
    _copyright = "GPL-3.0-or-later"
    _synopsis = "Create master dark"
    _description = (
        "Prototype to create a METIS Masterdark."
    )

    parameters = cpl.ui.ParameterList([
        cpl.ui.ParameterEnum(
            name="metis_det_dark.stacking.method",
            context="metis_det_dark",
            description="Name of the method used to combine the input images",
            default="average",
            alternatives=("add", "average", "median", "sigclip"),
        ),
    ])
    implementation_class = MetisDetDarkImpl

    def __init__(self):
        super().__init__()
        self.implementation = self.implementation_class(self)

    def run(self, frameset: cpl.ui.FrameSet, settings: Dict[str, Any]) -> cpl.ui.FrameSet:
        return self.implementation.run(frameset, settings)

