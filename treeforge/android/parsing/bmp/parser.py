from __future__ import annotations

from struct import unpack_from

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from treeforge.android.parsing.bmp.model import (
    AndroidParsedBmp,
)


class AndroidBmpParsingError(
    ValueError,
):
    pass


class AndroidBmpParser:
    """
    Decode literal BMP file and BITMAPINFOHEADER-compatible metadata.

    Recognition is intrinsic and content-driven. Filenames, SFLB resource
    names, and device-specific meaning are deliberately ignored.
    """

    _FILE_HEADER_SIZE = 14
    _MIN_DIB_HEADER_SIZE = 40
    _MINIMUM_SIZE = (
        _FILE_HEADER_SIZE
        + _MIN_DIB_HEADER_SIZE
    )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedBmp:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        data = artifact.path.read_bytes()

        if len(data) < self._MINIMUM_SIZE:
            raise AndroidBmpParsingError(
                "BMP artifact is too small: "
                f"{artifact.path}"
            )

        if data[:2] != b"BM":
            raise AndroidBmpParsingError(
                "artifact does not contain BMP magic: "
                f"{artifact.path}"
            )

        (
            file_size,
            _reserved1,
            _reserved2,
            pixel_data_offset,
        ) = unpack_from(
            "<IHHI",
            data,
            2,
        )

        dib_header_size = unpack_from(
            "<I",
            data,
            14,
        )[0]

        if (
            dib_header_size
            < self._MIN_DIB_HEADER_SIZE
        ):
            raise AndroidBmpParsingError(
                "unsupported BMP DIB header size "
                f"{dib_header_size}: {artifact.path}"
            )

        if (
            len(data)
            < self._FILE_HEADER_SIZE
            + dib_header_size
        ):
            raise AndroidBmpParsingError(
                "truncated BMP DIB header: "
                f"{artifact.path}"
            )

        (
            width,
            height,
            planes,
            bits_per_pixel,
            compression,
            image_size,
            horizontal_resolution,
            vertical_resolution,
            colors_used,
            important_colors,
        ) = unpack_from(
            "<iiHHIIiiII",
            data,
            18,
        )

        if file_size != len(data):
            raise AndroidBmpParsingError(
                "BMP declared file size does not match "
                f"canonical artifact size: declared={file_size}, "
                f"actual={len(data)}, path={artifact.path}"
            )

        if (
            pixel_data_offset < (
                self._FILE_HEADER_SIZE
                + dib_header_size
            )
            or pixel_data_offset > len(data)
        ):
            raise AndroidBmpParsingError(
                "BMP pixel-data offset is outside the "
                f"valid file structure: {artifact.path}"
            )

        if planes != 1:
            raise AndroidBmpParsingError(
                "BMP planes field must equal 1: "
                f"{artifact.path}"
            )

        return AndroidParsedBmp(
            artifact=artifact,
            file_size=file_size,
            pixel_data_offset=pixel_data_offset,
            dib_header_size=dib_header_size,
            width=width,
            height=height,
            planes=planes,
            bits_per_pixel=bits_per_pixel,
            compression=compression,
            image_size=image_size,
            horizontal_resolution=horizontal_resolution,
            vertical_resolution=vertical_resolution,
            colors_used=colors_used,
            important_colors=important_colors,
        )
