# Compressed assets

All 129 byte-pair-encoded streams decode with `tools/bpe.py` (port of `bpe_expand`, 4000:C760) and are re-encoded **byte-identically** by `tools/bpe_gage.py` (Gage compress.c, THRESHOLD 5). `make assets` writes decoded data and laid-out previews to `build/assets/` (git-ignored).

| family | streams | evidence | description |
|---|---:|---|---|
| tileset | 37 | structural | World 1 tiles: 2bpp terrain/object tiles; world from the level directory at 9:0000, whose Vision records for that world point into this bank (docs/level-data.md); not yet tied to a specific Vision |
| hint_sign | 32 | visual | in-Vision hint signboard: 14x9 tiles of Japanese text + icons, 7 tiles, 14 bytes |
| story_picture | 27 | visual | story illustration: 20x11 tiles (160x88 px) + 14 tiles + 12-byte palette block |
| menu_label | 10 | visual | menu option label (Japanese text strip), 19 tiles |
| gallery_picture | 6 | visual | Museum gallery artwork, framed 20x19-tile picture + 2 tiles + 8 bytes |
| pause_window | 4 | visual | pause / in-game menu window graphics |
| keyconfig_panel | 4 | visual | key-config panel (Type A / Type B) |
| yes_no_button | 4 | visual | Yes / No style button graphics + 12 bytes |
| banner_text | 4 | visual | large banner lettering: VISION / CLEAR / OVER / GOOD NIGHT |
| font_hud | 1 | visual | font digits / kana / HUD glyphs |

## Every stream

| offset | packed | unpacked | tiles | family | decoded SHA-1 |
|---|---:|---:|---:|---|---|
| 0000C | 4456 | 6120 | 382 | gallery_picture | `d471cce659302f0158aef21c5059b637714d7fb3` |
| 01174 | 3953 | 6120 | 382 | gallery_picture | `40a96b428808f250d153360314e1d3063a842a8f` |
| 020E5 | 3845 | 6120 | 382 | gallery_picture | `9de553f8dbe37cef1bc386ffa4646790386e289f` |
| 02FEA | 3825 | 6120 | 382 | gallery_picture | `a716828953cb13310bba1dc0ec5a784611ebfbae` |
| 03EDB | 3434 | 6120 | 382 | gallery_picture | `ceefb23ca61d404affdfc4bc8d13ab5ddb48963f` |
| 04C45 | 3587 | 6120 | 382 | gallery_picture | `7b20408c7082c148d150e8cce77e2c2dd36385a8` |
| 10004 | 997 | 1683 | 105 | pause_window | `3d45d4063d9b1ac561413d400b1637d8e074fde6` |
| 103E9 | 1088 | 1683 | 105 | pause_window | `e4379b2297866e5fc706920af6183525b32e2706` |
| 10881 | 282 | 306 | 19 | menu_label | `3143468bcc051a22596906bc27a35c063c8c0fe7` |
| 1099B | 300 | 306 | 19 | menu_label | `992b3f6fe268240b55fce9f2a93fb826087ab303` |
| 10AC7 | 272 | 306 | 19 | menu_label | `6e84d89be8d656172d116153a9d0cccaf1986619` |
| 10BD7 | 296 | 306 | 19 | menu_label | `4c86c8c0f8308f6c154a7288ed8829d22aa1fbff` |
| 10CFF | 265 | 306 | 19 | menu_label | `a852843d0eb2714dea16073e95a3d7fde270991d` |
| 10E08 | 284 | 306 | 19 | menu_label | `0b98e0c367ce8372898f1dd2a536da9c2573f56c` |
| 10F24 | 274 | 306 | 19 | menu_label | `62569e68e281ce9f0abd6fcf9586c61dea3231d5` |
| 11036 | 295 | 306 | 19 | menu_label | `7e0eef014ae1a709c7aa08f60a099e5dfc6a7693` |
| 1115D | 278 | 306 | 19 | menu_label | `8cea881b850f042b26738dac7a2616b34b3f8f60` |
| 11273 | 294 | 306 | 19 | menu_label | `8f9d04f50af347a5c6939e4d37f14f627c45e404` |
| 113A9 | 798 | 1360 | 85 | keyconfig_panel | `5389cea09cb6cfba49f41a3e88f745f7d00ad19e` |
| 116C7 | 802 | 1360 | 85 | keyconfig_panel | `7359bcc534c97faf1e3bf1bdb18d60ce8776fd65` |
| 119E9 | 172 | 204 | 12 | yes_no_button | `2dd729167bfb6090f3f91279ae19b77e2a319518` |
| 11A95 | 176 | 204 | 12 | yes_no_button | `755667368bf064bd37db1571a11bdf033664dc92` |
| 11B45 | 878 | 1360 | 85 | keyconfig_panel | `69d3f23546fb358b098f9e869e51979a663e5416` |
| 11EB3 | 890 | 1360 | 85 | keyconfig_panel | `ddc26435a5bbd753462e60de0c208338b5f98ec9` |
| 1222D | 169 | 204 | 12 | yes_no_button | `a2da07edcbb8b5f6a6a8faf473d7cf4ce56bc0e3` |
| 122D6 | 169 | 204 | 12 | yes_no_button | `15fe3e64c9a374d839f17d82cb702fe03a77e6cb` |
| 1237F | 1017 | 1683 | 105 | pause_window | `ff9d20f37f228bbbe0163a426aaeaeac884c932a` |
| 12778 | 1150 | 1683 | 105 | pause_window | `62fdf623580d9c60dbabed86df6a6dcd7aa2d4f5` |
| 12BF6 | 1402 | 2142 | 133 | hint_sign | `ee6de7026e93e8073ff49bc5bf4c07948f72ab37` |
| 13170 | 1300 | 2142 | 133 | hint_sign | `80523fb392dd7700e4d1cda01841adad4800a087` |
| 13684 | 1173 | 2142 | 133 | hint_sign | `39a4456e3b79269d55efe56eae231f2d6a049706` |
| 13B19 | 1362 | 2142 | 133 | hint_sign | `5a753b25a2874199eefe4d6c053abeafc0147ef5` |
| 1406B | 1277 | 2142 | 133 | hint_sign | `76ec3f9be9a84d5b44dac57112d7b62e0fcd3f4f` |
| 14568 | 1284 | 2142 | 133 | hint_sign | `45980c92b920b932e33e9e218708fc105aac5ad5` |
| 14A6C | 963 | 2142 | 133 | hint_sign | `9ffd5965cd72f6b998f25a8415e21b17126d0a79` |
| 14E2F | 1118 | 2142 | 133 | hint_sign | `ce5d4ce8a9db2a2a4096f8457b2e0079a5df6f1b` |
| 1528D | 1138 | 2142 | 133 | hint_sign | `da4271af5790a218fc191a71b75da8cc67c343f4` |
| 156FF | 1165 | 2142 | 133 | hint_sign | `72f94d361e55e210e7f76655d7dee1c43ad3e964` |
| 15B8C | 1332 | 2142 | 133 | hint_sign | `add098d46ca563f691915f38cebf0108c655c20c` |
| 160C0 | 1134 | 2142 | 133 | hint_sign | `07d9a674e3c7e614308b64054460c4ea3a5fa6dc` |
| 1652E | 1235 | 2142 | 133 | hint_sign | `be7e00a3ab7b90b9f8668b8eadcad11b45212776` |
| 16A01 | 1116 | 2142 | 133 | hint_sign | `b6a08e795c37bef7209a8b2e5221ace8da31ee20` |
| 16E5D | 1106 | 2142 | 133 | hint_sign | `95509a036709c94993adbba0ce973037dac2c694` |
| 172AF | 1177 | 2142 | 133 | hint_sign | `8aed909a2ee19593c697542d1b18e43ce8ff0e42` |
| 17748 | 1123 | 2142 | 133 | hint_sign | `c62c8b7a5122df19082eb18d34e02df7c705700f` |
| 17BAB | 1267 | 2142 | 133 | hint_sign | `a94ee09a198b3ffb490cddae21c867f9234308cb` |
| 1809E | 995 | 2142 | 133 | hint_sign | `ab3e617bdc22f8a2d5976d4d3f43173cb1210225` |
| 18481 | 1093 | 2142 | 133 | hint_sign | `699c3e0f963a493d5a01827b91013a273184faf3` |
| 188C6 | 1143 | 2142 | 133 | hint_sign | `126f7abde582d1b31713d3b24c10f473479f75f9` |
| 18D3D | 1248 | 2142 | 133 | hint_sign | `575413ac4963752d72f669b8500695f4e58e90bd` |
| 1921D | 1358 | 2142 | 133 | hint_sign | `c0a68eb78bbeb5f034b2054859909c5a7db41dc7` |
| 1976B | 1299 | 2142 | 133 | hint_sign | `692bcbd6ec5c8c5ed550cebd9f98adf45783ad16` |
| 19C7E | 1485 | 2142 | 133 | hint_sign | `54712760b3e66e4844546fcd18e9f5e741e6cd8c` |
| 1A24B | 1316 | 2142 | 133 | hint_sign | `66fd222d24d8c784597d28f0698da10ad576cb96` |
| 1A76F | 1275 | 2142 | 133 | hint_sign | `b9318bbd468b815bf2c40cbffcfd00db130d0885` |
| 1AC6A | 1136 | 2142 | 133 | hint_sign | `3fff6913fe3842f9cbc8cafe2d914477fea81e2a` |
| 1B0DA | 1271 | 2142 | 133 | hint_sign | `6b169e0338aa3a15ef56b5025cac02344f3d9001` |
| 1B5D1 | 1351 | 2142 | 133 | hint_sign | `bd74a6fe15122d905277917ee000259319bb8889` |
| 1BB18 | 1342 | 2142 | 133 | hint_sign | `f849180b71439ad385732a4f469b70db27cd1c63` |
| 1C056 | 1172 | 2142 | 133 | hint_sign | `6eb18af5fb75cefa78920a8f15b07a9d6ba9fcef` |
| 37300 | 471 | 510 | 31 | banner_text | `053728cbce678ecaf1ec311328d0699dccb43793` |
| 374D7 | 448 | 510 | 31 | banner_text | `07e8c5d8b2497e7dccb6b23ed72b276fdd5ae633` |
| 37697 | 408 | 459 | 28 | banner_text | `c2d7d8a392703f8dad50331e516dbb9cd9d3f750` |
| 3782F | 826 | 1224 | 76 | banner_text | `fce3a10b4e2a6e10d238df14dff2d3551f3e69f5` |
| 91124 | 1827 | 2288 | 143 | tileset | `187946894ebd734cfc0d2834660212d520757025` |
| 91847 | 1887 | 2672 | 167 | tileset | `0411e3bfb92337ed52ee9547f2f3c996ec47b89a` |
| 91FA6 | 1838 | 2576 | 161 | tileset | `c8a65f177964990f8e36efe1e9dec6ffa63e6e58` |
| 926D4 | 1808 | 2544 | 159 | tileset | `e708c8e755368a8bc95b8d0490ffb05e0cf3939e` |
| 92DE4 | 1904 | 2576 | 161 | tileset | `149f4f2d9b1e2c23492d4083fdce7165993c0eee` |
| 93554 | 1729 | 2400 | 150 | tileset | `6f7e7fae943f915c8c5476aa4d0e54a72d385001` |
| A0B9C | 1665 | 2096 | 131 | tileset | `b1a7d9215a2108b9e8357ab9048cb144d98e219c` |
| A121D | 1560 | 2000 | 125 | tileset | `b85e3b49b476a802993038ec4932364b076b84f8` |
| A1835 | 1568 | 2016 | 126 | tileset | `accc58db661fa73353459fdd48d45046271b5266` |
| A1E55 | 1472 | 1856 | 116 | tileset | `933f1e05bff73499f96e32d685624dd643bda441` |
| A2415 | 1612 | 2080 | 130 | tileset | `3ea0637cb887f4d6eceab2e20938d1bc123d0262` |
| A2A61 | 1164 | 1440 | 90 | tileset | `cbe1aed7bc9a25ff28b59cae461bde4c631b38ce` |
| AA6B0 | 3427 | 4448 | 278 | tileset | `15cddeab58443b29894273559b5f6d06864c2fb6` |
| B018C | 1832 | 2512 | 157 | tileset | `77f7bd26c61abeb9b3f440d7989890dbbf0f004c` |
| B08B4 | 1745 | 2384 | 149 | tileset | `de1ea27a089e27efb5d86f83256997a4b26ff8a6` |
| B0F85 | 1595 | 2112 | 132 | tileset | `2f86fa8e42eb4395fb4111b42d11a44e382fa3a7` |
| B15C0 | 1750 | 2224 | 139 | tileset | `aa86cffe7f8218a0109bec0ecbeb2ca1355be1ba` |
| B1C96 | 1683 | 2176 | 136 | tileset | `36c37c450af1c4af55ce3511deb251e934f8881e` |
| B2329 | 1768 | 2288 | 143 | tileset | `a7ed57c24a1aa27137f9852f1aa66f6245d7e1d0` |
| C018C | 1018 | 1696 | 106 | tileset | `20e09b9d0064d742a9ab749832bdb611f8398eae` |
| C0586 | 1367 | 2144 | 134 | tileset | `297eadd7e009f24635535365cad18dce30698750` |
| C0ADD | 1309 | 2016 | 126 | tileset | `4e21da4819aac2395794abe19fa710e7f76406b4` |
| C0FFA | 1293 | 2000 | 125 | tileset | `eaa611d4f7ae34f63c7b96f5d40ad118c7bc80d6` |
| C1507 | 1159 | 1856 | 116 | tileset | `f70dcc040f6e21e9479a3d3d0afbe9b9121ddeca` |
| C198E | 1298 | 2032 | 127 | tileset | `02733b24df9a3c267a9447ea4b258b6a04ba0c02` |
| D2884 | 1322 | 2128 | 133 | tileset | `b3a0ca847acb4607dce481d643ba2fa2e4951593` |
| D2DAE | 1199 | 1968 | 123 | tileset | `3469b32b8a6ec12ce02aa92cf48b4a97aa9dec47` |
| D325D | 1289 | 2160 | 135 | tileset | `87695dc5271017f247cf1b7bfaf65f16bae0ee38` |
| D3766 | 1332 | 2144 | 134 | tileset | `89f4d0d119cdcc166f6ca177b01a26538a5a1276` |
| D3C9A | 1272 | 2032 | 127 | tileset | `937a6caeafde7c1c04387f75a2e7c69f80973dba` |
| D4192 | 1271 | 2032 | 127 | tileset | `c1e667a00f44a3161f291535d97b5b49e4abeda7` |
| E018C | 1145 | 1408 | 88 | tileset | `d918447409ef72415c44c2103f68fb27fa6fe521` |
| E0605 | 1123 | 1392 | 87 | tileset | `b72d740c3966e531af824ea7883a63a0b41b6e20` |
| E0A68 | 1239 | 1584 | 99 | tileset | `040f97b99f3b7199f4f550b4e944ea0d135d63ac` |
| E0F3F | 1142 | 1408 | 88 | tileset | `20b59288c42971a7526bb339a1e62086b369a2bc` |
| E13B5 | 1304 | 1632 | 102 | tileset | `c5f4ec08511af5c89e95ab516e4a6c66de8632de` |
| E18CD | 1202 | 1520 | 95 | tileset | `4c9241ddb91605b4fead305c04cf60fd71b0dc13` |
| F0038 | 2354 | 3756 | 234 | story_picture | `0bfadb03251ad9eafe9ed9a61371ce9bc7a6afe1` |
| F096A | 2045 | 3756 | 234 | story_picture | `590268e7210f04547bbab0bf4ef2216db21f9a14` |
| F1167 | 937 | 3756 | 234 | story_picture | `2ecacb8a1429aa392d97541dbf4325f2678a130e` |
| F1510 | 1862 | 3756 | 234 | story_picture | `172845937ef114d5b12210b9ba601d5bc1c392a7` |
| F1C56 | 1631 | 3756 | 234 | story_picture | `240e579edad29a51da4930529d8c7fd2e7f1b678` |
| F22B5 | 1581 | 3756 | 234 | story_picture | `d051622a0679646c5ab65bdab288ad250ac8949b` |
| F28E2 | 2085 | 3756 | 234 | story_picture | `16b501d7aa102a842a878f8f6f930d0e2f055cd8` |
| F3107 | 2698 | 3756 | 234 | story_picture | `c103c791345f78064878526b9d8a278d2fbe497b` |
| F3B91 | 2315 | 3756 | 234 | story_picture | `42a8d242ee3310cb03d3aa0b0a7b103ad4ac978a` |
| F449C | 2444 | 3756 | 234 | story_picture | `9dbbfc121f6d609940dc07222594300cb9d28067` |
| F4E28 | 2224 | 3756 | 234 | story_picture | `a193debd2700d02ce1c5849211dd355cb85c290b` |
| F56D8 | 1814 | 3756 | 234 | story_picture | `eaf3882bd4246df498d9bf485915da52215638d9` |
| F5DEE | 2444 | 3756 | 234 | story_picture | `13ee87b3b1537e68fb76f96ae7cfd0f0c050dd7d` |
| F677A | 2351 | 3756 | 234 | story_picture | `462427be4215ebf88f488e0dbf0e978d45166a4b` |
| F70A9 | 2992 | 3756 | 234 | story_picture | `c07411dcbca9adbdd2c436eea0a9c75ec6aa1bd6` |
| F7C59 | 2615 | 3756 | 234 | story_picture | `200674006c3b4ffd0aa4d7c5079db365c1638a43` |
| F8690 | 2324 | 3756 | 234 | story_picture | `5cfe5d7d7cb953c89c2b8f500320d5eafe90aa0e` |
| F8FA4 | 2526 | 3756 | 234 | story_picture | `85a1ef436dd5c26d65edadc4625276859117c71b` |
| F9982 | 2990 | 3756 | 234 | story_picture | `b6b7405387065cc0f689d7ec8603c062061113a7` |
| FA530 | 3360 | 3756 | 234 | story_picture | `d2164a05269ed150d8aac6f7929b53232ff759a2` |
| FB250 | 2333 | 3756 | 234 | story_picture | `738af996a62dc1ae5d8c96a90184af5aee984cb4` |
| FBB6D | 2079 | 3756 | 234 | story_picture | `26cc137bf7ad751e82f3c8f3d400fa2bec913edc` |
| FC38C | 3450 | 3756 | 234 | story_picture | `06ef709ef09c9e196f63e0798b49a956630c199a` |
| FD106 | 1972 | 3756 | 234 | story_picture | `d79f4a520c5bbcf7117ce11a222cad3d334dbdfa` |
| FD8BA | 2216 | 3756 | 234 | story_picture | `44075fd6bbe2097a027c64ee48de6ec6f40f3a79` |
| FE162 | 2400 | 3756 | 234 | story_picture | `e0d8f507c32a84856e66a74a35e8a21b6d1baae9` |
| FEAC2 | 1381 | 3756 | 234 | story_picture | `dfd11b89e893cea2eaa95cf3010a6a7e45c5ee1e` |
| FF027 | 1173 | 1808 | 113 | font_hud | `b531b26333c30d0b6ac639bbba563abb655aa1ec` |
