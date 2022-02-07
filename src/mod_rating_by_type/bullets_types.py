import string

from django.utils.translation import pgettext_lazy
from .report import TOTAL_HITS, TOTAL_RECEIVED, ALL_TAKEN, BOMBS, ROCKETS, ORDINANCE


def take_first(elem):
    return elem[0]


def translate_ammo_breakdown(ammo_breakdown):
    result = {
        TOTAL_HITS: [],
        TOTAL_RECEIVED: [],
        ALL_TAKEN: ammo_breakdown[ALL_TAKEN],
        BOMBS: {
            TOTAL_HITS: [],
            TOTAL_RECEIVED: [],
            ALL_TAKEN: ammo_breakdown[ORDINANCE][BOMBS][ALL_TAKEN]
        },
        ROCKETS: {
            TOTAL_HITS: [],
            TOTAL_RECEIVED: [],
            ALL_TAKEN: ammo_breakdown[ORDINANCE][ROCKETS][ALL_TAKEN]
        },
    }

    for ammo, hits in ammo_breakdown[TOTAL_HITS].items():
        result[TOTAL_HITS].append((translate_bullet(ammo), hits))
    for ammo, received in ammo_breakdown[TOTAL_RECEIVED].items():
        result[TOTAL_RECEIVED].append((translate_bullet(ammo), received))
    result[TOTAL_HITS].sort(key=take_first)
    result[TOTAL_RECEIVED].sort(key=take_first)

    for ordinance_type in [BOMBS, ROCKETS]:
        for ammo, hits in ammo_breakdown[ORDINANCE][ordinance_type][TOTAL_HITS].items():
            result[ordinance_type][TOTAL_HITS].append((translate_bullet(ammo), hits))
        for ammo, hits in ammo_breakdown[ORDINANCE][ordinance_type][TOTAL_RECEIVED].items():
            result[ordinance_type][TOTAL_RECEIVED].append((translate_bullet(ammo), hits))
        result[ordinance_type][TOTAL_HITS].sort(key=take_first)
        result[ordinance_type][TOTAL_RECEIVED].sort(key=take_first)

    return result


def translate_damage_log_bullets(hits):
    result = [''] * len(hits)
    sorted_names = sorted([translate_bullet(ammo) for ammo in hits])
    for ammo in hits:
        ammo_name = translate_bullet(ammo)
        times = hits[ammo]
        if times > 1:
            result[sorted_names.index(ammo_name)] = '{} X {}'.format(times, ammo_name)
        else:
            result[sorted_names.index(ammo_name)] = str(ammo_name)
    return ', '.join(result)


def translate_bullet(bullet_type):
    bullet_type = bullet_type.upper()
    if bullet_type in bullet_types:
        return bullet_types[bullet_type]
    else:
        return bullet_type


bullet_types = {
    'BULLET_ENG_11X59_AP': pgettext_lazy('bullet_type', '11mm Vickers'),
    'BULLET_ENG_7-7X56_AP': pgettext_lazy('bullet_type', '.303 British'),
    'BULLET_GBR_11X59_AP': pgettext_lazy('bullet_type', '11mm Vickers'),
    'BULLET_GER_13X64_AP': pgettext_lazy('bullet_type', 'MG 131 (AP)'),
    'BULLET_GER_13X64_HE': pgettext_lazy('bullet_type', 'MG 131 (HE)'),
    'BULLET_GER_7-92X57_AP': pgettext_lazy('bullet_type', 'MG 17 (AP)'),
    'BULLET_GER_792X57_SS': pgettext_lazy('bullet_type', 'MG 17 (SS)'),
    'BULLET_ITA_12-7X81_AP': pgettext_lazy('bullet_type', 'Breda 12.7mm (AP)'),
    'BULLET_ITA_12-7X81_HE': pgettext_lazy('bullet_type', 'Breda 12.7mm (HE)'),
    'BULLET_ITA_7-7X56_AP': pgettext_lazy('bullet_type', ' Breda 7.7mm'),
    'BULLET_PISTOL': pgettext_lazy('bullet_type', 'Pistol bullet'),
    'BULLET_RUS_12-7X108_AP': pgettext_lazy('bullet_type', 'UB (AP)'),
    'BULLET_RUS_12-7X108_HE': pgettext_lazy('bullet_type', 'UB (HE)'),
    'BULLET_RUS_7-62X54_AP': pgettext_lazy('bullet_type', 'ShKAS (AP)'),
    'BULLET_USA_12-7X99_AP': pgettext_lazy('bullet_type', '.50 BMG'),
    'BULLET_USA_7-62X63_AP': pgettext_lazy('bullet_type', '.30-06 Springfield'),
    'NPC_BULLET_GER_7-92': pgettext_lazy('bullet_type', 'MG 34'),
    'NPC_BULLET_GER_7-92_AP_short': pgettext_lazy('bullet_type', 'MG 34'),
    'NPC_BULLET_RUS_7-62_AP_short': pgettext_lazy('bullet_type', '7.62 Soviet'),
    'NPC_BULLET_RUS_7-62X4': pgettext_lazy('bullet_type', '4x 7.62 Soviet'),
    'NPC_SHELL_RUS_122_HE': pgettext_lazy('bullet_type', '122mm Soviet'),
    'NPC_SHELL_RUS_130_HE': pgettext_lazy('bullet_type', '130mm Soviet'),
    'NPC_SHELL_USA_155_HE': pgettext_lazy('bullet_type', '155mm Soviet'),
    'NPC_SHELL_USA_90_CV': pgettext_lazy('bullet_type', 'M2 90mm (APHE)'),
    'NPC_SHELL_USA_90_HE': pgettext_lazy('bullet_type', 'M2 90mm (HE)'),
    'SHELL_GER_15X96_AP': pgettext_lazy('bullet_type', 'MG 151/15 (AP)'),
    'SHELL_GER_15X96_HE': pgettext_lazy('bullet_type', 'MG 151/15 (HE)'),
    'SHELL_GER_20X82_AP': pgettext_lazy('bullet_type', 'MG 151/20 (AP)'),
    'SHELL_GER_20X82_HE': pgettext_lazy('bullet_type', 'MG 151/20 (HE)'),
    'SHELL_GER_37X263_AP': pgettext_lazy('bullet_type', 'BK 3,7 (AP)'),
    'SHELL_GER_37X263_HE': pgettext_lazy('bullet_type', 'BK 3,7 (HE)'),
    'SHELL_RUS_122_HE': pgettext_lazy('bullet_type', '122mm Soviet (HE)'),
    'SHELL_RUS_122_HT': pgettext_lazy('bullet_type', '122mm Soviet (HEAT)'),
    'SHELL_RUS_20X99_AP': pgettext_lazy('bullet_type', 'ShVAK (AP)'),
    'SHELL_RUS_20X99_HE': pgettext_lazy('bullet_type', 'ShVAK (HE)'),
    'SHELL_RUS_23X152_AP': pgettext_lazy('bullet_type', 'VYA-23 (AP)'),
    'SHELL_RUS_23X152_HE': pgettext_lazy('bullet_type', 'VYA-23 (HE)'),
    'SHELL_RUS_37X195_AP': pgettext_lazy('bullet_type', 'SH-37 (AP)'),
    'SHELL_RUS_37X195_HE': pgettext_lazy('bullet_type', 'SH-37 (HE)'),
    'SHELL_RUS_37X198_AP': pgettext_lazy('bullet_type', 'NS-37 (AP)'),
    'SHELL_RUS_37X198_HE': pgettext_lazy('bullet_type', 'NS-37 (HE)'),
    'SHELL_RUS_76_naval_HE': pgettext_lazy('bullet_type', '76.2mm 34-K'),
    'SHELL_USA_37X145_AP': pgettext_lazy('bullet_type', 'M4 Cobra (AP)'),
    'SHELL_USA_37X145_HE': pgettext_lazy('bullet_type', 'M4 Cobra (HE)'),
    'SHELL_USA_76_CV': pgettext_lazy('bullet_type', '76mm M5 (APHE)'),
    'SHELL_USA_76_HE': pgettext_lazy('bullet_type', '76mm M5 (HE)'),
    'NPC_SHELL_ENG_76_HE': pgettext_lazy('bullet_type', '76mm British (HE)'),
    'NPC_SHELL_GER_105_HE': pgettext_lazy('bullet_type', '105mm German (HE)'),
    'NPC_SHELL_GER_20_AP': pgettext_lazy('bullet_type', 'Flak 38 (AP)'),
    'NPC_SHELL_GER_20_HE': pgettext_lazy('bullet_type', 'Flak 38 (HE)'),
    'NPC_SHELL_GER_37_CV': pgettext_lazy('bullet_type', 'Flak 36'),
    'NPC_SHELL_GER_37_HE': pgettext_lazy('bullet_type', '37mm Pak-35 (HE)'),
    'NPC_SHELL_GER_37X250_AP': pgettext_lazy('bullet_type', '37mm German Flak (AP)'),
    'NPC_SHELL_GER_37X250_HE': pgettext_lazy('bullet_type', '37mm German Flak (HE)'),
    'NPC_SHELL_GER_37X263_AP': pgettext_lazy('bullet_type', '37mm German Flak (AP)'),
    'NPC_SHELL_GER_37X263_HE': pgettext_lazy('bullet_type', '37mm German Flak (HE)'),
    'NPC_SHELL_GER_50_AP': pgettext_lazy('bullet_type', '50mm German (AP)'),
    'NPC_SHELL_GER_50_HE': pgettext_lazy('bullet_type', '50mm German (HE)'),
    'NPC_SHELL_GER_75_AP': pgettext_lazy('bullet_type', '75mm German (AP)'),
    'NPC_SHELL_GER_75_HE': pgettext_lazy('bullet_type', '75mm German (HE)'),
    'NPC_SHELL_GER_77_HE': pgettext_lazy('bullet_type', '77mm German (HE)'),
    'NPC_SHELL_GER_88_AP': pgettext_lazy('bullet_type', '88mm German Flak (AP)'),
    'NPC_SHELL_GER_88_HE': pgettext_lazy('bullet_type', '88mm German Flak (HE)'),
    'NPC_SHELL_RUS_100_HE': pgettext_lazy('bullet_type', '100mm Soviet (AP)'),
    'NPC_SHELL_RUS_152_HE': pgettext_lazy('bullet_type', '152mm Soviet (HE)'),
    'NPC_SHELL_RUS_25_AP': pgettext_lazy('bullet_type', '25mm 72-K (AP)'),
    'NPC_SHELL_RUS_25_HE': pgettext_lazy('bullet_type', '25mm 72-K (HE)'),
    'NPC_SHELL_RUS_37_AP': pgettext_lazy('bullet_type', '37mm Soviet (AP)'),
    'NPC_SHELL_RUS_37_HE': pgettext_lazy('bullet_type', '37mm Soviet (HE)'),
    'NPC_SHELL_RUS_45_AP': pgettext_lazy('bullet_type', '45mm Soviet (AP)'),
    'NPC_SHELL_RUS_45_CV': pgettext_lazy('bullet_type', '45mm Soviet (APHE)'),
    'NPC_SHELL_RUS_45_HE': pgettext_lazy('bullet_type', '45mm Soviet (HEAT)'),
    'NPC_SHELL_RUS_57_AP': pgettext_lazy('bullet_type', '57mm Soviet (AP)'),
    'NPC_SHELL_RUS_57_CV': pgettext_lazy('bullet_type', '57mm Soviet (APHE)'),
    'NPC_SHELL_RUS_57_HE': pgettext_lazy('bullet_type', '57mm Soviet (HE) '),
    'NPC_SHELL_RUS_76_AP': pgettext_lazy('bullet_type', '76mm Soviet (AP)'),
    'NPC_SHELL_RUS_76_HE': pgettext_lazy('bullet_type', '76mm Soviet (HE)'),
    'NPC_SHELL_RUS_76_NAVAL_HE': pgettext_lazy('bullet_type', '76mm Soviet Naval (HE)'),
    'NPC_SHELL_RUS_85_AP': pgettext_lazy('bullet_type', '85mm Soviet (AP)'),
    'NPC_SHELL_RUS_85_CV': pgettext_lazy('bullet_type', '85mm Soviet (APHE)'),
    'NPC_SHELL_RUS_85_HE': pgettext_lazy('bullet_type', '85mm Soviet (HE)'),
    'SHELL_ENG_115_HE': pgettext_lazy('bullet_type', '115mm British'),
    'SHELL_ENG_20X110_AP': pgettext_lazy('bullet_type', 'Hispano (AP)'),
    'SHELL_ENG_20X110_HE': pgettext_lazy('bullet_type', 'Hispano (HE)'),
    'SHELL_ENG_40X158_AP': pgettext_lazy('bullet_type', '40mm Vickers (AP)'),
    'SHELL_ENG_40X158_HE': pgettext_lazy('bullet_type', '40mm Vickers (HE)'),
    'SHELL_GER_105_HE': pgettext_lazy('bullet_type', '105mm German (HE)'),
    'SHELL_GER_105_HT': pgettext_lazy('bullet_type', '105mm German (HEAT)'),
    'SHELL_GER_150_HE': pgettext_lazy('bullet_type', '150mm German (HE)'),
    'SHELL_GER_30X184_AP': pgettext_lazy('bullet_type', 'MK 108 (AP)'),
    'SHELL_GER_30X184_HE': pgettext_lazy('bullet_type', 'MK 108 (HE)'),
    'SHELL_GER_50_CV': pgettext_lazy('bullet_type', '50mm German (APHE)'),
    'SHELL_GER_50_HE': pgettext_lazy('bullet_type', '50mm German (HE)'),
    'SHELL_GER_50_HV': pgettext_lazy('bullet_type', '50mm German (HVAP)'),
    'SHELL_GER_75_CV': pgettext_lazy('bullet_type', '75mm German (APHE)'),
    'SHELL_GER_75_HE': pgettext_lazy('bullet_type', '75mm German (HE)'),
    'SHELL_GER_75_HT': pgettext_lazy('bullet_type', '75mm German (HEAT)'),
    'SHELL_GER_75_HV': pgettext_lazy('bullet_type', '75mm German (HVAP)'),
    'SHELL_GER_88_AP': pgettext_lazy('bullet_type', '88mm German (AP)'),
    'SHELL_GER_88_CV': pgettext_lazy('bullet_type', '88mm German (APHE)'),
    'SHELL_GER_88_HE': pgettext_lazy('bullet_type', '88mm German (HE)'),
    'SHELL_GER_88_HE_KWK43': pgettext_lazy('bullet_type', '88mm German'),
    'SHELL_GER_88_HV': pgettext_lazy('bullet_type', '88mm German (HVAP)'),
    'SHELL_RUS_100_HE': pgettext_lazy('bullet_type', '100mm Soviet (HE)'),
    'SHELL_RUS_130_CV': pgettext_lazy('bullet_type', '100mm Soviet (APHE)'),
    'SHELL_RUS_130_HE': pgettext_lazy('bullet_type', '130mm Soviet (HE)'),
    'SHELL_RUS_152_CV': pgettext_lazy('bullet_type', '152mm Soviet (APHE)'),
    'SHELL_RUS_152_HE': pgettext_lazy('bullet_type', '152mm Soviet (HE)'),
    'SHELL_RUS_25X218_AP': pgettext_lazy('bullet_type', '25mm 72-K (AP)'),
    'SHELL_RUS_25X218_HE': pgettext_lazy('bullet_type', '25mm 72-K (HE)'),
    'SHELL_RUS_76_AP': pgettext_lazy('bullet_type', '76mm Soviet (AP)'),
    'SHELL_RUS_76_CV': pgettext_lazy('bullet_type', '76mm Soviet (APHE)'),
    'SHELL_RUS_76_HE': pgettext_lazy('bullet_type', '76mm Soviet (HE)'),
    'SHELL_RUS_76_HV': pgettext_lazy('bullet_type', '76mm Soviet (HVAP)'),
    'SHELL_USA_155_HE': pgettext_lazy('bullet_type', '155mm Soviet (HE)'),
    'SHELL_USA_75_AP': pgettext_lazy('bullet_type', '75mm Soviet (AP)'),
    'SHELL_USA_75_CV': pgettext_lazy('bullet_type', '75mm Soviet (APHE)'),
    'SHELL_USA_75_HE': pgettext_lazy('bullet_type', '75mm Soviet (HE)'),
    'BOMB_FRA_20KG': pgettext_lazy('bullet_type', '20kg Bomb French'),
    'BOMB_FRA_40KG': pgettext_lazy('bullet_type', '40kg Bomb French'),
    'BOMB_FRA_8KG': pgettext_lazy('bullet_type', '8kg Bomb French'),
    'BOMB_GBR_112LB': pgettext_lazy('bullet_type', ' H.E.R.L. 112 lbs'),
    'BOMB_GBR_20LB': pgettext_lazy('bullet_type', '24 lb Cooper'),
    'BOMB_GBR_230LB': pgettext_lazy('bullet_type', '230 lb bomb British'),
    'BOMB_GBR_24LB': pgettext_lazy('bullet_type', '24 lb Cooper'),
    'BOMB_GBR_GPB250': pgettext_lazy('bullet_type', '250 lb GP'),
    'BOMB_GBR_GPB500': pgettext_lazy('bullet_type', '500 lb GP'),
    'BOMB_GBR_MC1000': pgettext_lazy('bullet_type', '1000 lb MC'),
    'BOMB_GBR_MC250MK2': pgettext_lazy('bullet_type', '250 lb MC Mk 2'),
    'BOMB_GBR_MC500': pgettext_lazy('bullet_type', '500 lb MC'),
    'BOMB_GBR_MC500MK7': pgettext_lazy('bullet_type', '500 lb MC Mk 7'),
    'BOMB_GER_10KG': pgettext_lazy('bullet_type', '10 kg. P.u.W'),
    'BOMB_GER_12KG': pgettext_lazy('bullet_type', '12.5 kg. P.u.W'),
    'BOMB_GER_50KG': pgettext_lazy('bullet_type', '50 kg. P.u.W '),
    'BOMB_GER_SC1000': pgettext_lazy('bullet_type', 'SC 1000'),
    'BOMB_GER_SC1000_190': pgettext_lazy('bullet_type', 'SC 1000 (190)'),
    'BOMB_GER_SC1800': pgettext_lazy('bullet_type', 'SC 1800'),
    'BOMB_GER_SC250': pgettext_lazy('bullet_type', 'SC 250'),
    'BOMB_GER_SC250_87': pgettext_lazy('bullet_type', 'SC 250 (Ju 87)'),
    'BOMB_GER_SC2500': pgettext_lazy('bullet_type', 'SC 2500'),
    'BOMB_GER_SC50': pgettext_lazy('bullet_type', 'SC 50'),
    'BOMB_GER_SC500': pgettext_lazy('bullet_type', 'SC 500'),
    'BOMB_GER_SC500_87': pgettext_lazy('bullet_type', 'SC 500 (Ju 87)'),
    'BOMB_GER_SD70': pgettext_lazy('bullet_type', 'SD 70'),
    'BOMB_ITA_100T': pgettext_lazy('bullet_type', '100-T'),
    'BOMB_ITA_50T': pgettext_lazy('bullet_type', '50-T'),
    'BOMB_RUS_FAB100M': pgettext_lazy('bullet_type', 'FAB-100M'),
    'BOMB_RUS_FAB100M_P39': pgettext_lazy('bullet_type', 'FAB-100M (P39)'),
    'BOMB_RUS_FAB250SV': pgettext_lazy('bullet_type', 'FAB-250sv'),
    'BOMB_RUS_FAB250SV_P40': pgettext_lazy('bullet_type', 'FAB-250sv (P40)'),
    'BOMB_RUS_FAB250TSK': pgettext_lazy('bullet_type', 'FAB-250'),
    'BOMB_RUS_FAB500M': pgettext_lazy('bullet_type', 'FAB-500M'),
    'BOMB_RUS_FAB500M_P40': pgettext_lazy('bullet_type', 'FAB-500M (P40)'),
    'BOMB_RUS_FAB50SV': pgettext_lazy('bullet_type', 'FAB-50sv'),
    'BOMB_USA_M64': pgettext_lazy('bullet_type', 'M64'),
    'BOMB_USA_M65': pgettext_lazy('bullet_type', 'M65'),
    'BOMB_USA_M66': pgettext_lazy('bullet_type', 'M66'),
    'CLUSTER_RUS_PTAB2515': pgettext_lazy('bullet_type', 'PTAB-2.5-1.5'),
    'CLUSTER_RUS_PTAB2515_HIT': pgettext_lazy('bullet_type', 'PTAB-2.5-1.5'),
    'NPC_TORPEDO_53-38': pgettext_lazy('bullet_type', 'Type 53 Torpedo'),
    'NPC_TORPEDO_G7a-53,0,G7a': pgettext_lazy('bullet_type', 'G7a Torpedo'),
    'RKT_FRA_LEPRIEUR': pgettext_lazy('bullet_type', 'Le Prieur'),
    'RKT_FRA_LEPRIEURHE': pgettext_lazy('bullet_type', 'Le Prieur (HE)'),
    'RKT_GBR_RP3AP': pgettext_lazy('bullet_type', 'RP-3 (AP)'),
    'RKT_GBR_RP3AP_HIT': pgettext_lazy('bullet_type', 'RP-3 (AP)'),
    'RKT_GBR_RP3AP_MK3': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (AP)'),
    'RKT_GBR_RP3HE': pgettext_lazy('bullet_type', 'RP-3 (HE)'),
    'RKT_GBR_RP3HE_DOUBLE': pgettext_lazy('bullet_type', 'RP-3 double (HE)'),
    'RKT_GBR_RP3HE_MK3': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (HE)'),
    'RKT_GBR_RP3MK3AP': pgettext_lazy('bullet_type', 'RP-3 Mk3 (AP)'),
    'RKT_GBR_RP3MK3HE': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (HE) '),
    'RKT_GBR_RP3MK3TLAP': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (AP)'),
    'RKT_GBR_RP3MK3TLHE': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (HE)'),
    'RKT_GBR_RP3MK3TUAP': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (AP)'),
    'RKT_GBR_RP3MK3TUHE': pgettext_lazy('bullet_type', 'RP-3 Mk 3 (HE)'),
    'RKT_GER_PB1': pgettext_lazy('bullet_type', 'PB1'),
    'RKT_GER_PB1_HIT': pgettext_lazy('bullet_type', 'PB1'),
    'RKT_GER_PB1_M8': pgettext_lazy('bullet_type', 'PB1 M8'),
    'RKT_GER_R4M': pgettext_lazy('bullet_type', 'R4M'),
    'RKT_GER_WGR21': pgettext_lazy('bullet_type', 'Werfer-Granate 21'),
    'RKT_GER_WGR21_1000': pgettext_lazy('bullet_type', 'Werfer-Granate 21'),
    'RKT_GER_WGR21_1200': pgettext_lazy('bullet_type', 'Werfer-Granate 21'),
    'RKT_GER_WGR21_800': pgettext_lazy('bullet_type', 'Werfer-Granate 21'),
    'RKT_RUS_RBS82': pgettext_lazy('bullet_type', 'RBS-82'),
    'RKT_RUS_RBS82_HIT': pgettext_lazy('bullet_type', 'RBS-82'),
    'RKT_RUS_ROFS132': pgettext_lazy('bullet_type', 'ROFS-132'),
    'RKT_RUS_ROS82': pgettext_lazy('bullet_type', 'ROS-82'),
    'RKT_RUS_ROS82_1000,0,ROS-82,РО': pgettext_lazy('bullet_type', 'ROS-82'),
    'RKT_RUS_ROS82_600,0,ROS-82,РО': pgettext_lazy('bullet_type', 'ROS-82'),
    'RKT_RUS_ROS82_800,0,ROS-82,РО': pgettext_lazy('bullet_type', 'ROS-82'),
    'RKT_USA_M8': pgettext_lazy('bullet_type', 'M8'),
    'Rocket 280 MM HE': pgettext_lazy('bullet_type', 'Rocket 280 mm HE'),
}
