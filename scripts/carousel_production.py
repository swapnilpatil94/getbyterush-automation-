#!/usr/bin/env python3
"""Production wrapper for the GetByteRush carousel renderer.

Uses the renderer's own deterministic browser QA. The renderer writes each
slide at 1080x1350 and fails only on genuine geometry/text overflow.
"""

import carousel_generator as renderer


if __name__ == "__main__":
    renderer.main()
