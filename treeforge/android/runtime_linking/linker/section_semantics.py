from __future__ import annotations


class AndroidRuntimeLinkerSectionSemantics:
    """
    Central linkerconfig vocabulary for built-in BASE section roles.

    These are Runtime Linking semantics rather than canonical device facts.
    Profile-defined additional sections remain data-driven.
    """

    SYSTEM = "system"
    VENDOR = "vendor"
    PRODUCT = "product"
    UNRESTRICTED = "unrestricted"
    POSTINSTALL = "postinstall"
    ISOLATED = "isolated"

    @staticmethod
    def _validate(
        section_name: str,
    ) -> None:
        if (
            not isinstance(
                section_name,
                str,
            )
            or not section_name
        ):
            raise ValueError(
                "section_name must be a non-empty string"
            )

    @classmethod
    def is_system(
        cls,
        section_name: str,
    ) -> bool:
        cls._validate(section_name)
        return section_name == cls.SYSTEM

    @classmethod
    def is_vendor(
        cls,
        section_name: str,
    ) -> bool:
        cls._validate(section_name)
        return section_name == cls.VENDOR

    @classmethod
    def is_product(
        cls,
        section_name: str,
    ) -> bool:
        cls._validate(section_name)
        return section_name == cls.PRODUCT

    @classmethod
    def is_unrestricted(
        cls,
        section_name: str,
    ) -> bool:
        cls._validate(section_name)
        return section_name == cls.UNRESTRICTED

    @classmethod
    def is_postinstall(
        cls,
        section_name: str,
    ) -> bool:
        cls._validate(section_name)
        return section_name == cls.POSTINSTALL

    @classmethod
    def is_isolated(
        cls,
        section_name: str,
    ) -> bool:
        cls._validate(section_name)
        return section_name == cls.ISOLATED

    @classmethod
    def standard_system_namespace_name(
        cls,
        section_name: str,
    ) -> str:
        cls._validate(section_name)

        if (
            cls.is_system(section_name)
            or cls.is_unrestricted(section_name)
            or cls.is_postinstall(section_name)
        ):
            return "default"

        return "system"

    @classmethod
    def vndk_enabled(
        cls,
        section_name: str,
        *,
        vendor_vndk_defined: bool,
        product_vndk_defined: bool,
    ) -> bool:
        cls._validate(section_name)

        if cls.is_vendor(
            section_name
        ):
            return vendor_vndk_defined

        if cls.is_product(
            section_name
        ):
            return product_vndk_defined

        return False

    @classmethod
    def apex_visibility_policy(
        cls,
        section_name: str,
    ) -> tuple[
        bool,
        bool,
    ] | None:
        """
        Return BuildSection APEX visibility policy for one built-in section.

        The tuple is:

            (allows_jni_libraries, allows_public_libraries)

        None means the section is not one of the canonical BuildSection
        roles for which Runtime Linking owns APEX visibility semantics.
        Postinstall is intentionally None because Android constructs it
        outside BuildSection. Profile-defined additional sections likewise
        remain unresolved unless their semantics are explicitly modeled.
        """

        cls._validate(
            section_name
        )

        if (
            cls.is_system(
                section_name
            )
            or cls.is_unrestricted(
                section_name
            )
            or cls.is_isolated(
                section_name
            )
        ):
            return (
                True,
                True,
            )

        if (
            cls.is_vendor(
                section_name
            )
            or cls.is_product(
                section_name
            )
        ):
            return (
                False,
                True,
            )

        return None

    @classmethod
    def allows_jni_apex_visibility(
        cls,
        section_name: str,
    ) -> bool:
        """
        Whether BuildSection JNI-library visibility applies to this
        canonical built-in linker section.
        """

        policy = cls.apex_visibility_policy(
            section_name
        )

        return (
            policy is not None
            and policy[0]
        )

    @classmethod
    def allows_public_library_apex_visibility(
        cls,
        section_name: str,
    ) -> bool:
        """
        Whether BuildSection public-library visibility applies to this
        canonical built-in linker section.
        """

        policy = cls.apex_visibility_policy(
            section_name
        )

        return (
            policy is not None
            and policy[1]
        )
