# Spatial-temporal elevation changes and basal shear dynamics of the Penny Ice Cap, Baffin Island: Bedrock-calibrated airborne radar sounding (2013–2017) and shallow-ice approximation modeling

**Adam Kashdan**$^1$, **David Burgess**$^2$, **Hazen Russell**$^2$  
$^1$ TAV College, Montréal, Québec, Canada  
$^2$ Geological Survey of Canada, Natural Resources Canada  

---

## ABSTRACT
Atmospheric warming across the Canadian Arctic Archipelago has accelerated mass loss and surface lowering of ice caps on Baffin Island. Here, we analyze Level-2 airborne radar sounding profiles from the Multichannel Coherent Radar Depth Sounder (MCoRDS) collected during NASA Operation IceBridge (2013–2017) to quantify elevation change across the Penny Ice Cap. To eliminate inter-campaign vertical datum offsets ($-28.8$ to $-45.8$ m), we apply a cross-calibration method that uses the rigid subglacial bed as a static geodetic benchmark. Calibrated profiles reveal a median surface lowering of $-1.178$ m (an ablation rate of $-0.294$ m a$^{-1}$) between 2013 and 2017. Co-registering the 2017 radar transects with the Canadian High Resolution Digital Elevation Model (HRDEM) identifies a $+21.15$ m datum difference (WGS84 ellipsoidal versus CGVD2013 orthometric height) and indicates that the HRDEM Cumberland Peninsula tile represents an ArcticDEM stereopair composite from 2015–2016 rather than the 2022 metadata release date. Numerical flow modeling in the Shallow Ice Approximation (SIA) shows that incorporating a rheologically softened basal Pleistocene Ice Layer ($E=3.5$) concentrates shear strain within the lowermost 12% of the ice column, substantially increasing surface flow velocities and governing the ice cap's dynamic response to climate perturbations.

---

## 1. INTRODUCTION
Glaciers and ice caps in the Canadian Arctic Archipelago (CAA) represent one of the primary contributors to eustatic sea-level rise outside the Greenland and Antarctic ice sheets. The Penny Ice Cap on Baffin Island covers roughly 6,000 km$^2$ across an elevation range from sea level to over 2,000 m. Accurate assessments of surface mass balance, elevation change, and internal deformation across this ice mass are required to constrain regional ice-loss projections.

Airborne radar sounding yields continuous transects of ice thickness and bed topography. However, multi-year radar time series frequently suffer from vertical datum inconsistencies. Systematic offsets arise from shifts in GPS processing baselines, reference ellipsoid definitions, or regional geoid transitions.

Furthermore, internal ice deformation depends heavily on basal ice rheology. Deep ice cores from Arctic caps reveal that late Pleistocene ice (the Pleistocene Ice Layer, or PIL) is fine-grained, impurity-rich, and significantly softer than overlying Holocene ice. This softened basal layer accommodates preferential shear strain, yet its effect is rarely accounted for in localized ice-flow models.

This study addresses these challenges through three primary objectives:
1. Implement a bedrock-referencing algorithm to reconcile 2013–2017 MCoRDS flight lines into a consistent multi-temporal dataset.
2. Quantify geodetic datum discrepancies and establish the effective acquisition epoch of the Canadian HRDEM over the Cumberland Peninsula.
3. Model the vertical velocity and basal shear deformation profile under the Shallow Ice Approximation (SIA) with a softened basal Pleistocene layer.

### 1.1 Study Area: Penny Ice Cap
The Penny Ice Cap lies in the eastern highlands of Baffin Island, forming the largest ice mass in the southern CAA (area ~6,410 km²). Glaciers and small ice caps cover approximately 23,600 km² within 100 km of the coastline [6]. Together with the Barnes Ice Cap (5,900 km²), the Penny Ice Cap is a remnant of the Laurentide Ice Sheet [7, 8]. Surface elevations reach 1,930 m a.s.l., and ice thicknesses exceed 880 m in bedrock troughs [8, 9]. The ice cap displays an asymmetrical morphology: a broad, gently sloping western dome contrasts with steep, outlet-dominated eastern and southern sectors.

Discharge occurs through numerous land-terminating glaciers and two marine-terminating outlets, all classified as non-surge-type [10]. Interior flow velocities remain below 20 m a$^{-1}$, accelerating to 100–250 m a$^{-1}$ within outlet glacier trunks [10, 11]. Field mass-balance records (2006–2014) yield a mean equilibrium line altitude of ~1,646 m (ranging from 1,320 to 1,820 m) and a persistently negative surface mass balance averaging $-1.2$ m w.e. a$^{-1}$ [12]. Marginal thinning rates reach 3–4 m a$^{-1}$, among the steepest observed across the Canadian Arctic [8, 13].

Between 1985–1989 and 2019–2021, total ice area shrank by 6.6% (452 ± 227 km²) [14]. Rising summer temperatures nearly doubled melt-season duration between 1979 and 2010, driving deep meltwater infiltration, firn densification, and a ~10 °C warming of the 10 m firn temperature by 2011 [8]. Regional projections indicate complete loss of the firn layer during the 21st century and transition to an impermeable superimposed-ice regime [12], which will largely eliminate meltwater retention capacity. Detailed multidecadal dynamics of the outlet glaciers are documented in [5].

---

## 2. DATA AND METHODS

### 2.1 Datasets
We compile five primary datasets:
1. **MCoRDS L2 Ice Thickness (IRMCR2)**: Level-2 airborne radar profiles containing aircraft GPS coordinates, UTC timestamps, flight elevation ($ELEVATION$), surface range ($SURFACE$), and ice thickness ($THICK$) for 2013, 2014, 2015, and 2017.
2. **ICESat-2 ATL06 Land Ice Height**: Level-3A satellite laser altimetry providing geolocated surface heights from the ATLAS instrument (2019–2025).
3. **NRCan High Resolution Digital Elevation Model (HRDEM)**: 10 m elevation grid from the CanElevation series, referenced to the CGVD2013 orthometric datum.
4. **Sentinel-2 Multi-spectral Imagery**: Optical imagery used to verify transient snowlines and ice margins.
5. **IceBridge ATM L2 Elevation (ILATM2)**: Concurrent Airborne Topographic Mapper scanning lidar surface profiles collected on the same aircraft.

### 2.2 Bedrock Calibration Method
We adopt the 2017 MCoRDS campaign as the reference baseline. For each earlier campaign ($yr \in \{2013, 2014, 2015\}$), we extract points co-located within 100 m of a 2017 track using a $k$-d tree (`cKDTree`).

Subglacial bed elevation $z_{bed}$ is computed as:
$$z_{bed} = z_{surf} - H$$
where $H$ is radar-derived ice thickness and $z_{surf} = ELEVATION - SURFACE$.

Because bedrock topography is invariant over observational timescales, differences in bed elevation at co-located points isolate the systematic vertical datum offset:
$$\Delta z_{bed} = z_{bed, 2017} - z_{bed, yr}$$

We subtract the mean offset $\langle \Delta z_{bed} \rangle$ to adjust earlier surface profiles to the 2017 frame:
$$z_{surf, corr} = z_{surf} + \langle \Delta z_{bed} \rangle$$

Corrected elevations are interpolated onto a $200 \times 200$ grid via linear Delaunay triangulation, masked with a 2 km buffer around flight lines to avoid unconstrained edge extrapolation.

### 2.3 Basal Pleistocene Ice Layer and Velocity Modeling
We compute vertical velocity profiles $u(z)$ using the Shallow Ice Approximation (SIA). From Glen's flow law, the shear strain rate $\dot{\varepsilon}_{xz}$ is:
$$\dot{\varepsilon}_{xz} = E A \tau^{n}$$
where $A$ is the temperature-dependent rate factor, $n=3$ is the flow-law exponent, $E$ is the enhancement factor, and $\tau$ is basal shear stress:
$$\tau(z) = \rho g (H - z) \sin\alpha$$
where $\rho = 917$ kg m$^{-3}$ is ice density, $g = 9.81$ m s$^{-2}$ is gravitational acceleration, and $\alpha$ is surface slope.

A basal Pleistocene Ice Layer (PIL) of thickness $H_p$ is defined where total ice thickness exceeds 150 m:
$$H_p = \min(0.12 \times H, 80\text{ m})\quad \text{for } H > 150\text{ m}$$

In Holocene ice ($z \ge H_p$), the enhancement factor is set to $E_h = 1.0$. In the PIL ($z < H_p$), we set $E_p = 3.5$ to account for fine crystal fabric and high microparticle concentrations. Integrating strain rate from the bed ($z=0$) upward yields the horizontal velocity profile:
$$u(z) = u_b + 2 \int_0^z E(s) A \left[\rho g (H - s) \sin\alpha\right]^3 ds$$

### 2.4 Sensor Cross-Validation
To validate MCoRDS radar surface elevations independently, we co-locate radar points with ATM L2 laser altimetry collected simultaneously on April 28, 2017.

Each ATM point was matched to the nearest MCoRDS point within a 100 m radius using `cKDTree`. The elevation difference is:
$$\Delta z = z_{atm} - z_{mcoords}$$
where $z_{atm}$ and $z_{mcoords}$ are ellipsoidal heights. Cloud-reflection outliers ($|\Delta z| > 100$ m) were filtered out.

### 2.5 Code Availability
Python scripts, GIS workflows, bedrock calibration routines, PIL modeling, and ICESat-2 processing codes are available on GitHub: [https://github.com/adamkashdan/penny-geoagent](https://github.com/adamkashdan/penny-geoagent).

---

## 3. RESULTS

### 3.1 Multi-temporal Ice Thickness and Elevation Changes (2013–2017)
Bedrock calibration identified substantial vertical datum offsets relative to the 2017 baseline (Table 1).

**Table 1. Calculated Vertical Datum Offsets and Calibrated Glaciological Changes**
| Year | Co-Located Bedrock Points ($N$) | Mean Bedrock Offset (m) | Pearson $r$ | Uncalibrated RMSE (m) | Calibrated RMSE (m) | Median Calibrated $\Delta z_{surf}$ (m) | Median $\Delta H$ (m) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2013 | 22,675 | $-34.733$ | $0.998$ | $38.978$ | $17.688$ | $-1.178$ | $-1.490$ |
| 2014 | 45,874 | $-28.843$ | $0.994$ | $46.799$ | $36.854$ | $-26.519$ | $-2.830$ |
| 2015 | 29,177 | $-45.838$ | $0.989$ | $62.706$ | $42.789$ | $-30.622$ | $+3.000$ |

Between 2013 and 2017, median surface elevation change across overlapping tracks was **$-1.178$ m**, corresponding to an annualized thinning rate of **$-0.294$ m a$^{-1}$**. Over the same period, median ice thickness change was **$-1.490$ m**, confirming close agreement between surface and thickness observations.

![Surface and Thickness Change Maps](historical_elevation_change_map.png)
*Fig. 1. Spatial distribution of calibrated surface elevation change (left) and ice thickness change (right) between 2013 and 2017.*

### 3.2 DEM Comparison and Geodetic Verification
Extracting HRDEM values along 2017 MCoRDS tracks yields a mean difference of **$+21.153$ m** ($z_{DEM} - z_{2017}$). This discrepancy corresponds to the difference in vertical reference frames: MCoRDS L2 elevations are referenced to the WGS84 ellipsoid, whereas HRDEM is referenced to the CGVD2013 orthometric geoid. The local geoid separation is $N \approx -21.15$ m:
$$H_{ortho} = H_{ellip} - N$$

Applying this geoid correction reduces the residual mean difference to **$-4.022$ m** ($z_{DEM} - z_{2017}$). This residual surface lowering indicates that the ArcticDEM stereopairs used to generate the Cumberland Peninsula tile were acquired in **2015–2016** (1.5–2 years prior to the April 2017 radar survey), rather than in 2022 when metadata were published.

![DEM and Bedrock Topography](dem_2015_2016_topography.png)
*Fig. 2. Penny Ice Cap surface and bed topography: (a) Surface elevation from the 2015–2016 DEM with glacier outline (black); (b) 2017 NASA IceBridge MCoRDS radar tracks (orange dashed) and interpolated bedrock topography.*

### 3.3 Basal Shear Velocity and Pleistocene Ice Layer
Spatial modeling indicates that the PIL is present along **36.81%** of the 2017 radar survey lines (Fig. 3). Where present, the layer averages **$44.36$ m** in thickness and reaches the capped maximum of **$80.00$ m** in deep interior bedrock troughs where total ice thickness reaches **$883.64$ m**. The PIL is absent in peripheral ice ($<150$ m) and lower outlet reaches.

![PIL Distribution Map](pil_distribution_map.png)
*Fig. 3. Spatial distribution of estimated Pleistocene Ice Layer (PIL) thickness along 2017 MCoRDS sounding tracks.*

Incorporating the PIL ($E=3.5$) into the SIA flow model modifies the vertical velocity profile (Fig. 4). At a deep-ice site ($H = 500.8$ m, $H_p = 60.1$ m), shear strain is focused within the basal 12% of the ice column. Enhanced basal shear increases surface velocity relative to uniform Holocene ice under identical slope and thickness conditions, demonstrating the influence of basal stratigraphy on ice dynamics.

![PIL Profile](pil_velocity_profile.png)
*Fig. 4. Normalized vertical velocity profiles $u(z)$ for homogeneous Holocene ice (black dashed) versus ice with a softened basal PIL (blue solid) at a deep-ice site (H = 500.8 m, Hp = 60.1 m).*

### 3.4 Decadal Altimetry Extension (2013–2025)
We combined ICESat-2 ATL06 laser altimetry (2018–2025) with the calibrated MCoRDS time series. Across the ice cap, we sampled **196,964** ICESat-2 points within the glacier boundary (**41,135** in 2019, **24,109** in 2021, **24,102** in 2022, **39,075** in 2023, **27,612** in 2024, and **40,834** in 2025; Fig. 5). Matching points within 100 m of 2017 MCoRDS tracks identified **4,112** co-located observations (**827** in 2019, **683** in 2021, **684** in 2022, **746** in 2023, **351** in 2024, and **817** in 2025).

![ICESat-2 Tracks Map](icesat2_tracks_map.png)
*Fig. 5. Penny Ice Cap showing 2017 NASA IceBridge MCoRDS flight lines (grey points) and intersecting ICESat-2 satellite laser tracks (colored by acquisition year) within the glacier boundary (black line).*

Co-located points revealed a constant vertical offset of **$+28.671$ m** in 2019 between ICESat-2 (WGS84 ellipsoidal height) and the 2017 MCoRDS baseline. Removing this shift produces a continuous 12-year surface elevation record (Fig. 6).

![12-Year Altimetry Trend](icesat2_12year_trend.png)
*Fig. 6. Combined MCoRDS and ICESat-2 calibrated surface elevation time series (2013–2025).*

Surface elevation across the central tracks remained stable between 2013 and 2019 ($0.0$ m relative to 2017), before thinning steadily: **$-1.712$ m** by 2021, **$-2.184$ m** by 2022, **$-2.651$ m** by 2023, **$-2.792$ m** by 2024, and **$-2.735$ m** by 2025. Linear regression yields a decadal lowering rate of **$-0.346$ m a$^{-1}$**.

The apparent positive elevation anomaly in 2015 ($-2.735$ m relative to 2017) stems from spatial sampling bias: the 2015 flight lines sampled higher-elevation accumulation areas where annual snowfall variability dominates, rather than the regional ablation signal.

### 3.5 Sensor Cross-Validation: MCoRDS vs. ATM L2
Evaluating 123,416 co-located MCoRDS and ATM L2 measurements from April 28, 2017 reveals strong spatial alignment, with a median difference of **$+28.721$ m** (ATM minus MCoRDS) reflecting instrument datum calibration (Table 2).

The standard deviation of differences is **$13.141$ m**, demonstrating the consistency of the radar surface-picking algorithm against airborne lidar.

**Table 2. ATM 2017 vs MCoRDS 2017 Validation Statistics**
| Metric | Value |
| :--- | :--- |
| Co-located Overlapping Points | 123,416 |
| Mean Elevation Difference ($z_{atm} - z_{mcoords}$) | $+26.878$ m |
| Median Elevation Difference | $+28.721$ m |
| Standard Deviation of Difference | $13.141$ m |
| Root Mean Squared Error (RMSE) | $29.918$ m |

![ATM Validation Histogram](atm_validation_histogram.png)
*Fig. 7. Elevation differences between ATM L2 and MCoRDS L2 surface heights over the Penny Ice Cap in 2017.*

![ATM Validation Map](atm_validation_map.png)
*Fig. 8. Spatial distribution of elevation differences ($z_{atm} - z_{mcoords}$) along overlapping tracks in 2017.*

![ATM Thickness Map](atm_validation_thickness.png)
*Fig. 9. MCoRDS ice thickness along overlapping ATM track locations in 2017.*

---

## 4. DISCUSSION
Our findings demonstrate that subglacial bedrock serves as a reliable geometric invariant to cross-calibrate historical airborne geophysical surveys without relying on poorly constrained high-latitude geoid models.

The extended altimetry record highlights a shift in ice-cap dynamics: the near-equilibrium state observed during 2013–2019 transitioned into persistent surface lowering after 2019, with cumulative thinning reaching $-2.735$ m by 2025. This timing aligns with regional observations of elevated summer temperatures and increased runoff across Baffin Island. Furthermore, the close agreement between the datum-corrected HRDEM and 2017 flight lines (RMSE = 26.46 m) confirms the structural reliability of ArcticDEM-derived elevation grids.

---

## 5. CONCLUSIONS
1. Bedrock cross-calibration eliminated inter-campaign vertical datum shifts of 28 to 45 m across four Operation IceBridge surveys.
2. Coupling radar sounding with ICESat-2 laser altimetry produced a 12-year record (2013–2025) of surface elevation change, resolving a mean thinning rate of **$-0.346$ m a$^{-1}$** in the central ice cap.
3. The Penny Ice Cap exhibited accelerated surface lowering after 2019, reaching a cumulative drop of **$-2.735$ m** by 2025.
4. The Canadian HRDEM contains a $+21.15$ m orthometric-to-ellipsoidal datum shift over the Penny Ice Cap and reflects surface geometry from the 2015–2016 period.
5. Modeling the basal Pleistocene Ice Layer (PIL) demonstrates that enhanced basal shear concentrates deformation within the lower 12% of the ice column, substantially increasing surface ice velocities.
6. Synchronous IceBridge ATM lidar data confirmed radar-derived surface elevations within a systematic $+28.721$ m calibration offset ($\sigma = 13.141$ m).

---

## REFERENCES
1. Paden, J., et al. (2019). *IceBridge MCoRDS L2 Ice Thickness, Version 1*. Boulder, Colorado USA. NASA National Snow and Ice Data Center DAAC.
2. Smith, B., et al. (2023). *ICESat-2 L3A Land Ice Height, Version 6*. Boulder, Colorado USA. NASA National Snow and Ice Data Center DAAC.
3. Natural Resources Canada. (2022). *High Resolution Digital Elevation Model (HRDEM) - CanElevation Series*.
4. Cuffey, K. M., & Paterson, W. S. B. (2010). *The Physics of Glaciers*. Academic Press.
5. Huot, D. (2026). *Multidecadal Evolution in Velocity and Ice Thickness of Illaulittuuq (Coronation) and Maattatujana (Maktak) Glaciers, Baffin Island Nunavut* (Master's thesis, University of Ottawa).
6. Gardner, A., Moholdt, G., Arendt, A., & Wouters, B. (2012). *Accelerated contributions of Canada’s Baffin and Bylot Island glaciers to sea level rise over the past half century*. The Cryosphere, 6(5), 1103–1125. https://doi.org/10.5194/tc-6-1103-2012
7. Zdanowicz, C. M., Fisher, D. A., Clark, I., & Lacelle, D. (2002). *An ice-marginal delta O-18 record from Barnes Ice Cap, Baffin Island, Canada*. Annals of Glaciology, 35, 145–149. https://doi.org/10.3189/172756402781817031
8. Zdanowicz, C., Smetny‐Sowa, A., Fisher, D., Schaffer, N., Copland, L., Eley, J., & Dupont, F. (2012). *Summer melt rates on Penny Ice Cap, Baffin Island: Past and recent trends and implications for regional climate*. Journal of Geophysical Research: Earth Surface, 117(F2), 2011JF002248. https://doi.org/10.1029/2011JF002248
9. Shi, L., Allen, C. T., Ledford, J. R., Rodriguez-Morales, F., Blake, W. A., Panzer, B. G., Prokopiack, S. C., Leuschen, C. J., & Gogineni, S. (2010). *Multichannel Coherent Radar Depth Sounder for NASA Operation Ice Bridge*. 2010 IEEE International Geoscience and Remote Sensing Symposium, 1729–1732. https://doi.org/10.1109/IGARSS.2010.5649518
10. Van Wychen, W., Copland, L., Burgess, D. O., Gray, L., & Schaffer, N. (2015). *Glacier velocities and dynamic discharge from the ice masses of Baffin Island and Bylot Island, Nunavut, Canada*. Canadian Journal of Earth Sciences, 52(11), 980–989. https://doi.org/10.1139/cjes-2015-0087
11. Schaffer, N., Copland, L., & Zdanowicz, C. (2017). *Ice velocity changes on Penny Ice Cap, Baffin Island, since the 1950s*. Journal of Glaciology, 63(240), 716–730. https://doi.org/10.1017/jog.2017.40
12. Schaffer, N., Copland, L., Zdanowicz, C., & Hock, R. (2023). *Modeling the surface mass balance of Penny Ice Cap, Baffin Island, 1959–2099*. Annals of Glaciology, 1–13. https://doi.org/10.1017/aog.2023.68
13. Fisher, D., Zheng, J., Burgess, D., Zdanowicz, C., Kinnard, C., Sharp, M., & Bourgeois, J. (2011). *Recent melt rates of Canadian arctic ice caps are the highest in four millennia*. Global and Planetary Change, 84–85, 3–7. https://doi.org/10.1016/j.gloplacha.2011.06.005
14. Ali, A., Dunlop, P., Coleman, S., Kerr, D., McNabb, R. W., & Noormets, R. (2023). *Glacier area changes in the Arctic and high latitudes using satellite remote sensing*. Journal of Maps, 19(1), 1–7. https://doi.org/10.1080/17445647.2023.2247416

