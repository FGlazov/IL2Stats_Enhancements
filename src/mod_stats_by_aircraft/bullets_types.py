from django.utils.translation import pgettext_lazy
from .aircraft_mod_models import (AVERAGES, INST, RECEIVED, GIVEN, TOTALS,
                                  multi_key_to_string, string_to_multikey)


def take_first(elem):
    return elem[0]


def render_ammo_breakdown(ammo_breakdown, filter_out_flukes=True):
    return {
        GIVEN: __render_sub_dict(ammo_breakdown[GIVEN], filter_out_flukes, fluke_threshold=0.1),
        RECEIVED: __render_sub_dict(ammo_breakdown[RECEIVED], filter_out_flukes),
    }


def __render_sub_dict(sub_dict, filter_out_flukes, fluke_threshold=0.05):
    result = []

    total_inst = 0
    for multi_key in sub_dict[TOTALS]:
        total_inst += sub_dict[TOTALS][multi_key][INST]

    for multi_key in sub_dict[TOTALS]:
        inst = sub_dict[TOTALS][multi_key][INST]
        if filter_out_flukes and (inst < 4 or inst / total_inst < fluke_threshold):
            continue

        keys = string_to_multikey(multi_key)
        mg_keys = [key for key in keys if 'BULLET' in key]
        cannon_keys = [key for key in keys if 'SHELL' in key]

        translated_mg_keys = sorted([translate_bullet(key) for key in mg_keys])
        translated_cannon_keys = sorted([translate_bullet(key) for key in cannon_keys])

        if translated_mg_keys and translated_cannon_keys:
            ammo_names = (multi_key_to_string(translated_cannon_keys, ' | ')
                          + " | " + multi_key_to_string(translated_mg_keys, ' | '))
        elif translated_mg_keys:
            ammo_names = multi_key_to_string(translated_mg_keys, ' | ')
        else:
            ammo_names = multi_key_to_string(translated_cannon_keys, ' | ')

        mg_avgs = [0] * len(mg_keys)
        cannon_avgs = [0] * len(cannon_keys)
        for mg_key in mg_keys:
            key_index = translated_mg_keys.index(translate_bullet(mg_key))
            mg_avgs[key_index] = sub_dict[AVERAGES][multi_key][mg_key]

        for cannon_key in cannon_keys:
            key_index = translated_cannon_keys.index(translate_bullet(cannon_key))
            cannon_avgs[key_index] = sub_dict[AVERAGES][multi_key][cannon_key]

        if mg_avgs and cannon_avgs:
            avg_use = (multi_key_to_string(cannon_avgs, ' | ') + ' | ' + multi_key_to_string(mg_avgs, ' | '))
        elif mg_avgs:
            avg_use = multi_key_to_string(mg_avgs, ' | ')
        else:
            avg_use = multi_key_to_string(cannon_avgs, ' | ')

        result.append((ammo_names, avg_use))

    result.sort(key=take_first)
    return result


def translate_bullet(bullet_type):
    if bullet_type in bullet_types:
        return bullet_types[bullet_type]
    else:
        return bullet_type


bullet_types = {
    'BULLET_ENG_11x59_AP': pgettext_lazy('bullet_type', '11mm Vickers'),
    'BULLET_ENG_7-7x56_AP': pgettext_lazy('bullet_type', '.303 BMG'),
    'BULLET_GBR_11x59_AP': pgettext_lazy('bullet_type', '11mm Vickers'),
    'BULLET_GER_13x64_AP': pgettext_lazy('bullet_type', 'MG 131 (AP)'),
    'BULLET_GER_13x64_HE': pgettext_lazy('bullet_type', 'MG 131 (HE)'),
    'BULLET_GER_7-92x57_AP': pgettext_lazy('bullet_type', 'MG 17 (AP)'),
    'BULLET_GER_792x57_SS': pgettext_lazy('bullet_type', 'MG 17 (SS)'),
    'BULLET_ITA_12-7x81_AP': pgettext_lazy('bullet_type', 'Breda 12.7mm (AP)'),
    'BULLET_ITA_12-7x81_HE': pgettext_lazy('bullet_type', 'Breda 12.7mm (HE)'),
    'BULLET_ITA_7-7x56_AP': pgettext_lazy('bullet_type', ' Breda 7.7mm'),
    'BULLET_PISTOL': pgettext_lazy('bullet_type', 'Pistol bullet'),
    'BULLET_RUS_12-7x108_AP': pgettext_lazy('bullet_type', 'UB (AP)'),
    'BULLET_RUS_12-7x108_HE': pgettext_lazy('bullet_type', 'UB (HE)'),
    'BULLET_RUS_7-62x54_AP': pgettext_lazy('bullet_type', 'ShKAS (AP)'),
    'BULLET_USA_12-7x99_AP': pgettext_lazy('bullet_type', '.50 BMG'),
    'BULLET_USA_7-62x63_AP': pgettext_lazy('bullet_type', '.303 BMG'),
    'NPC_BULLET_GER_7-92': pgettext_lazy('bullet_type', 'MG 34'),
    'NPC_BULLET_GER_7-92_AP_short': pgettext_lazy('bullet_type', 'MG 34'),
    'NPC_BULLET_RUS_7-62_AP_short': pgettext_lazy('bullet_type', '7.62 Soviet'),
    'NPC_BULLET_RUS_7-62x4': pgettext_lazy('bullet_type', '4x 7.62 Soviet'),
    'NPC_SHELL_RUS_122_HE': pgettext_lazy('bullet_type', '122mm Soviet'),
    'NPC_SHELL_RUS_130_HE': pgettext_lazy('bullet_type', '130mm Soviet'),
    'NPC_SHELL_USA_155_HE': pgettext_lazy('bullet_type', '155mm Soviet'),
    'NPC_SHELL_USA_90_CV': pgettext_lazy('bullet_type', 'M2 90mm (APHE)'),
    'NPC_SHELL_USA_90_HE': pgettext_lazy('bullet_type', 'M2 90mm (HE)'),
    'SHELL_GER_15x96_AP': pgettext_lazy('bullet_type', 'MG 151/15 (AP)'),
    'SHELL_GER_15x96_HE': pgettext_lazy('bullet_type', 'MG 151/15 (HE)'),
    'SHELL_GER_20x82_AP': pgettext_lazy('bullet_type', 'MG 151/20 (AP)'),
    'SHELL_GER_20x82_HE': pgettext_lazy('bullet_type', 'MG 151/20 (HE)'),
    'SHELL_GER_37x263_AP': pgettext_lazy('bullet_type', 'BK 3,7 (AP)'),
    'SHELL_GER_37x263_HE': pgettext_lazy('bullet_type', 'BK 3,7 (HE)'),
    'SHELL_RUS_122_HE': pgettext_lazy('bullet_type', '122mm Soviet (HE)'),
    'SHELL_RUS_122_HT': pgettext_lazy('bullet_type', '122mm Soviet (HEAT)'),
    'SHELL_RUS_20x99_AP': pgettext_lazy('bullet_type', 'ShVAK (AP)'),
    'SHELL_RUS_20x99_HE': pgettext_lazy('bullet_type', 'ShVAK (HE)'),
    'SHELL_RUS_23x152_AP': pgettext_lazy('bullet_type', 'VYA-23 (AP)'),
    'SHELL_RUS_23x152_HE': pgettext_lazy('bullet_type', 'VYA-23 (HE)'),
    'SHELL_RUS_37x195_AP': pgettext_lazy('bullet_type', 'SH-37 (AP)'),
    'SHELL_RUS_37x195_HE': pgettext_lazy('bullet_type', 'SH-37 (HE)'),
    'SHELL_RUS_37x198_AP': pgettext_lazy('bullet_type', 'NS-37 (AP)'),
    'SHELL_RUS_37x198_HE': pgettext_lazy('bullet_type', 'NS-37 (HE)'),
    'SHELL_RUS_76_naval_HE': pgettext_lazy('bullet_type', '76.2mm 34-K'),
    'SHELL_USA_37x145_AP': pgettext_lazy('bullet_type', 'M4 Cobra (AP)'),
    'SHELL_USA_37x145_HE': pgettext_lazy('bullet_type', 'M4 Cobra (HE)'),
    'SHELL_USA_76_CV': pgettext_lazy('bullet_type', '76mm M5 (APHE)'),
    'SHELL_USA_76_HE': pgettext_lazy('bullet_type', '76mm M5 (HE)'),
    'NPC_SHELL_ENG_76_HE': pgettext_lazy('bullet_type', '76mm British (HE)'),
    'NPC_SHELL_GER_105_HE': pgettext_lazy('bullet_type', '105mm German (HE)'),
    'NPC_SHELL_GER_20_AP': pgettext_lazy('bullet_type', 'Flak 38 (AP)'),
    'NPC_SHELL_GER_20_HE': pgettext_lazy('bullet_type', 'Flak 38 (HE)'),
    'NPC_SHELL_GER_37_CV': pgettext_lazy('bullet_type', 'Flak 36'),
    'NPC_SHELL_GER_37_HE': pgettext_lazy('bullet_type', '37mm Pak-35 (HE)'),
    'NPC_SHELL_GER_37x250_AP': pgettext_lazy('bullet_type', '37mm German Flak (AP)'),
    'NPC_SHELL_GER_37x250_HE': pgettext_lazy('bullet_type', '37mm German Flak (HE)'),
    'NPC_SHELL_GER_37x263_AP': pgettext_lazy('bullet_type', '37mm German Flak (AP)'),
    'NPC_SHELL_GER_37x263_HE': pgettext_lazy('bullet_type', '37mm German Flak (HE)'),
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
    'NPC_SHELL_RUS_76_naval_HE': pgettext_lazy('bullet_type', '76mm Soviet Naval (HE)'),
    'NPC_SHELL_RUS_85_AP': pgettext_lazy('bullet_type', '85mm Soviet (AP)'),
    'NPC_SHELL_RUS_85_CV': pgettext_lazy('bullet_type', '85mm Soviet (APHE)'),
    'NPC_SHELL_RUS_85_HE': pgettext_lazy('bullet_type', '85mm Soviet (HE)'),
    'SHELL_ENG_115_HE': pgettext_lazy('bullet_type', '115mm British'),
    'SHELL_ENG_20x110_AP': pgettext_lazy('bullet_type', 'Hispano (AP)'),
    'SHELL_ENG_20x110_HE': pgettext_lazy('bullet_type', 'Hispano (HE)'),
    'SHELL_ENG_40x158_AP': pgettext_lazy('bullet_type', '40mm Vickers (AP)'),
    'SHELL_ENG_40x158_HE': pgettext_lazy('bullet_type', '40mm Vickers (HE)'),
    'SHELL_GER_105_HE': pgettext_lazy('bullet_type', '105mm German (HE)'),
    'SHELL_GER_105_HT': pgettext_lazy('bullet_type', '105mm German (HEAT)'),
    'SHELL_GER_150_HE': pgettext_lazy('bullet_type', '150mm German (HE)'),
    'SHELL_GER_30x184_AP': pgettext_lazy('bullet_type', 'MK 101 (AP)'),
    'SHELL_GER_30x184_HE': pgettext_lazy('bullet_type', 'MK 108 (HE)'),
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
    'SHELL_GER_88_HE_kwk43': pgettext_lazy('bullet_type', '88mm German'),
    'SHELL_GER_88_HV': pgettext_lazy('bullet_type', '88mm German (HVAP)'),
    'SHELL_RUS_100_HE': pgettext_lazy('bullet_type', '100mm Soviet (HE)'),
    'SHELL_RUS_130_CV': pgettext_lazy('bullet_type', '100mm Soviet (APHE)'),
    'SHELL_RUS_130_HE': pgettext_lazy('bullet_type', '130mm Soviet (HE)'),
    'SHELL_RUS_152_CV': pgettext_lazy('bullet_type', '152mm Soviet (APHE)'),
    'SHELL_RUS_152_HE': pgettext_lazy('bullet_type', '152mm Soviet (HE)'),
    'SHELL_RUS_25x218_AP': pgettext_lazy('bullet_type', '25mm 72-K (AP)'),
    'SHELL_RUS_25x218_HE': pgettext_lazy('bullet_type', '25mm 72-K (HE)'),
    'SHELL_RUS_76_AP': pgettext_lazy('bullet_type', '76mm Soviet (AP)'),
    'SHELL_RUS_76_CV': pgettext_lazy('bullet_type', '76mm Soviet (APHE)'),
    'SHELL_RUS_76_HE': pgettext_lazy('bullet_type', '76mm Soviet (HE)'),
    'SHELL_RUS_76_HV': pgettext_lazy('bullet_type', '76mm Soviet (HVAP)'),
    'SHELL_USA_155_HE': pgettext_lazy('bullet_type', '155mm Soviet (HE)'),
    'SHELL_USA_75_AP': pgettext_lazy('bullet_type', '75mm Soviet (AP)'),
    'SHELL_USA_75_CV': pgettext_lazy('bullet_type', '75mm Soviet (APHE)'),
    'SHELL_USA_75_HE': pgettext_lazy('bullet_type', '75mm Soviet (HE)'),
}
