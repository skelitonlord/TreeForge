# TreeForge

**TreeForge** is an open-source Android device bring-up framework for analyzing Android factory-image contents and reconstructing deterministic, reviewable Android device-tree inputs.

The initial validation target is the **Google Pixel Tablet (`tangorpro`) running Android 15**. TreeForge is being designed around immutable models, deterministic output, provenance preservation, provider-independent inputs, and test-driven development.

Everything is recorded and allows human intervention if needed. Treeforge will also provide a list and output of things it doesn’t know about so it can be handled manually in device/os specific modules. Once released, push requests will have to have matching test files as well and **WILL NOT BE ACCEPTED WITHOUT THEM** 

> **Development status**
>
> TreeForge is under active development and is not yet a finished production release.
> The current development checkpoint is init_boot reconstruction
> Commands and generated output may change before the first public beta.

alpha/beta, whatever I’m calling it, current info:

There will be a setup script released that will also double as the “updater” for source until I work on a gui. this setup script will hopefully be released this week, pending init_boot, and require access to my private organization/repo. Treeforge is currently 100% terminal and argument based. The alpha, as I guess I should really call it, is to hopefully have other pixel zips tested against it and make sure it passes the smoke tests still **currently ONLY android 15_r36 has been tested, and will remain that way until full release and android 16 can be brought up. it has a 20250505 release date for factory zips**

Treeforge in this state will not make bootable trees yet, as it’s still only about 40% done through the reconstruction. it will however populate device.mk and boardconfig.mk with what it can find if successful

super.img is currently not fully
implemented as I realized half way through that pixel tablet doesn’t use it and if I don’t need it right now, it’s waiting.

