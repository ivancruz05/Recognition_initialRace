"""HTTP backend - thin adapter over the detection module.

This package must not contain analysis logic. It translates HTTP into calls on
`detection` and back. Anything that smells like biomechanics belongs in
`detection/metrics/`, not here.
"""

__version__ = "1.0.0"
