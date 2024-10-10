from abc import ABCMeta, abstractmethod

import cpl
from cpl.core import Msg

from prototypes.inputs.base import PipelineInput


class PipelineInputSet(metaclass=ABCMeta):
    """
        The `PipelineInput` class is a singleton utility class for a recipe.
        It reads and filters the input FrameSet, categorizes the frames by their metadata,
        and finally stores them in its own attributes for further use.
        It also provides verification mechanisms and methods
        for extraction of additional information from the frames.

        Every `RecipeImpl` should have exactly one `InputSet` class (though possibly shared by more recipes though).
        Currently, we define them as internal classes of the corresponding `RecipeImpl`,
        but in Python it does not really matter much, they can be instatiated or derived from from the outside too.
    """

    inputs: [PipelineInput] = []

    def __init__(self, frameset: cpl.ui.FrameSet, **kwargs):
        """ Filter the input frameset, capture frames that match criteria and assign them to own attributes. """

    def verify(self):
        Msg.debug(self.__class__.__qualname__, f"Verifying the inputset {self.inputs}")

        for inp in self.inputs:
            inp.verify()
