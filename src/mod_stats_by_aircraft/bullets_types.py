from django.utils.translation import pgettext_lazy
from .aircraft_mod_models import (AVERAGES, INST, RECEIVED, GIVEN, TOTALS, PILOT_KILLS, STANDARD_DEVIATION,
                                  multi_key_to_string, string_to_multikey)
from .reservoir_sampling import get_samples
import numpy as np
from scipy.spatial.distance import cdist, euclidean
from sklearn.decomposition import PCA


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

        translated_mg_keys = sorted([str(translate_bullet(key)) for key in keys if 'BULLET' in key])
        translated_cannon_keys = sorted([str(translate_bullet(key)) for key in keys if 'SHELL' in key])

        samples = get_samples(sub_dict[TOTALS][multi_key], len(keys))
        ammo_names = ' | '.join(translated_cannon_keys + translated_mg_keys)

        avg_use = get_display_string(sub_dict[AVERAGES][multi_key], keys, translated_mg_keys, translated_cannon_keys)

        if STANDARD_DEVIATION in sub_dict[TOTALS][multi_key] and inst > 1:
            stds = get_display_string(sub_dict[TOTALS][multi_key][STANDARD_DEVIATION], keys, translated_mg_keys,
                                      translated_cannon_keys)
        else:
            stds = '-'

        medians = [round(median, 2) for median in geometric_median(samples)]
        medians = get_display_string(medians, keys, translated_mg_keys, translated_cannon_keys)

        if len(samples) >= 10:
            percentiles = [round(percentile_component, 2) for percentile_component in percentile(samples, 90)]
            percentiles = get_display_string(percentiles, keys, translated_mg_keys, translated_cannon_keys)
        else:
            percentiles = '-'

        pilot_kills = '-'
        pilot_kills_percent = '-'
        if PILOT_KILLS in sub_dict[TOTALS][multi_key]:
            pilot_kills = sub_dict[TOTALS][multi_key][PILOT_KILLS]
            pilot_kills_percent = round(100 * pilot_kills / max(inst, 1), 2)

        extra_info = {
            'key': multi_key,
            'instances': inst,
            'pilot_kills': pilot_kills,
            'pilot_kills_percent': pilot_kills_percent,
            "stds": stds,
            "medians": medians,
            "percentiles": percentiles,
        }
        result.append((ammo_names, avg_use, extra_info))

    result.sort(key=take_first)
    return result


def get_display_string(to_sort, keys, translated_mg_keys, translated_cannon_keys):
    if not to_sort:
        return '-'

    mg_result = [''] * len(translated_mg_keys)
    cannon_result = [''] * len(translated_cannon_keys)

    for i, key in enumerate(keys):
        if 'BULLET' in key:
            key_index = translated_mg_keys.index(translate_bullet(key))
            if type(to_sort) is dict:
                mg_result[key_index] = str(to_sort[key])
            else:
                mg_result[key_index] = str(to_sort[i])
        else:
            key_index = translated_cannon_keys.index(translate_bullet(key))
            if type(to_sort) is dict:
                cannon_result[key_index] = str(to_sort[key])
            else:
                cannon_result[key_index] = str(to_sort[i])

    return ' | '.join(cannon_result + mg_result)


def translate_bullet(bullet_type):
    if bullet_type in bullet_types:
        return bullet_types[bullet_type]
    else:
        return bullet_type


def geometric_median(X, eps=1e-3, max_iterations=50):
    """
    https://stackoverflow.com/a/30305181

    Computes the geometric median, which is a generalization of the median to multi-dimensional data.
    """
    if len(X) == 0:
        return []

    y = np.mean(X, 0)

    i = 0
    while True:
        D = cdist(X, [y])
        nonzeros = (D != 0)[:, 0]

        Dinv = 1 / D[nonzeros]
        Dinvs = np.sum(Dinv)
        W = Dinv / Dinvs
        T = np.sum(W * X[nonzeros], 0)

        num_zeros = len(X) - np.sum(nonzeros)
        if num_zeros == 0:
            y1 = T
        elif num_zeros == len(X):
            return y
        else:
            R = (T - y) * Dinvs
            r = np.linalg.norm(R)
            rinv = 0 if r == 0 else num_zeros / r
            y1 = max(0, 1 - rinv) * T + min(1, rinv) * y

        if euclidean(y, y1) < eps or i > max_iterations:
            return y1

        y = y1
        i += 1


def percentile(samples, threshold):
    """
    Retrieves the "percentile" at threshold, i.e. the 90th percentile if threshold = 90.

    Since the data is multidimensional (different kind of bullets hitting), it's not actually a percentile in this case.
    Still, since most of the data is highly correlated and "almost lies on a line" (most kills from players involve
    the same % of each bullet type hitting), we can instead try and find the line the data lies on and derive the
    percentiles from that.

    This is done by reducing the data into a single dimension using PCA (principal component analysis), taking the
    median on the reduced data, and then returning the domain into the orignal space.
    """
    if samples.shape[1] == 1:  # Edge case: Data is already 1D.
        return [np.percentile(samples.flatten(), threshold)]

    # Fit the PCA
    pca = PCA(n_components=1)
    pca.fit(samples)

    # Transform to 1D and take the percentile there
    reduced_samples = pca.transform(samples)
    reduced_percentile = np.percentile(reduced_samples, threshold)

    # Transform back to the original space and return
    return pca.inverse_transform(reduced_percentile).flatten()


bullet_types = {
    'BULLET_ENG_11x59_AP': pgettext_lazy('bullet_type', '11mm Vickers'),
    'BULLET_ENG_7-7x56_AP': pgettext_lazy('bullet_type', '.303 British'),
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
    'BULLET_USA_7-62x63_AP': pgettext_lazy('bullet_type', '.30-06 Springfield'),
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
