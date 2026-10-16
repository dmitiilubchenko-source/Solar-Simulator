# Ток массы и coordinate moments105–107

Продолжение [глобальной harmonicmap](harmonic-sphere-validation.md).
Model: instantaneous tracer current на одном t=const срезе static metric,
SI, fixed origin, explicit areal→smoothharmonic radial map; no recentering.
Мера dMb задана на срезе. Плотность σn=Wρb по собственному пространственному
объёму не отождествляется с comovingrestρb при ненулевой скорости.
Tracers не создают поле и не являются self-consistent rotating fluid.

## Определения и собственный вывод

[Klioner/Soffel2014,(103–107)](https://arxiv.org/html/1403.0024)
задаёт scalar lapse и пространственную метрику radialchart.
[Hartle1967,(109–113)](https://articles.adsabs.harvard.edu/pdf/1967ApJ...150.1005H)
задаёт baryon current иотдельную rest/internal split; pinnedPDF повторно
сверяется передfreshaudit. Дальнейшие matrix/tensor/current formulas —
наш вывод из coordinate differential иscalar/action definitions.

X=λ(r)x, λ=H(s)/s; differential A=λI+(H'−λ)nnᵀ, n=x/|x|,
radial/tangent eigenvalues H',λ>0. В центре λ=H'=scale, g_areal=I.
Position X=λx, velocity V=A v. **Position не равна A x** при нелинейной карте.
Canonical momentum is a covector: P=A^-T p, поскольку p·dx=P·dX.
Spatial metric gX=A^-T gx A^-1. Scalar lapse N не меняется при t'=t.
Cartesian density ofcurrent ρ*X=ρ*x/detA; dMb invariant.

Для SO(3)-equivariant radialmap X×P=x×p, даже если p имеет radialpart.
Контроль p·v=P·V иg(v,v)=gX(V,V) независим от уравнений сил.
При explicit quadratic particle actionLkin=Σm g(v,v)/(2N) получаем
p=m g v/N. Это низкоскоростной kinetic snapshot в фиксированной метрике,
без totalparticleenergy/restpotential ибез bodyfield/stress energy.
Одноразовый snapshot не доказывает temporalconservation E/J.

## Coordinate moments и независимая аналитика

D_areal=∫xxᵀdMb,D_harmonic=∫XXᵀdMb. Raw Euclidean
Cchart=tr(Dchart)I−Dchart иMchart=STF(Dchart) — coordinate bookkeeping,
не physical PNfluidinertia ине covariant tensor с простым centreJacobian.
В нелинейной карте D_harmonic нельзя заменить scale²D_areal или AD Aᵀ
с одним A во всём теле. Старый affine Newtonlimit из density_moments
остаётся верным для genuinely affine map, не для глобальной radialchart.

В audit suppliedcurrent σn/ρe=f(s)[1+nᵀQn+b·n], symmetricSTFQ,
f=0.4+0.2s²; chosen Q иb обеспечиваютpositive density.
Angular integrals: ∫shape dΩ=4π, ∫nshape dΩ=4πb/3,
∫nnᵀshape dΩ=4π(I/3+2Q/15). Сначала analytically fixedmoments,
затем независимый 3D Gauss/azimuthal quadrature; parameters не fit.

При ρe=3M/(4πR³),u=√(1−2Cs²) иU=I/3+2Q/15:
Mb=3M∫s²f/u ds,
first_areal=MR b∫s³f/u ds, first_harmonic=MR b∫s²Hf/u ds,
D_areal=3MR²U∫s⁴f/u ds, D_harmonic=3MR²U∫s²H²f/u ds.
Для v=Ω×x+κx иp=m gxv/N axialJ=[tr(DN)I−DN]Ω,
DN=3MR²U∫s⁴f/(uN)ds. Radialpart не входит вJ.
Kquad=Ωᵀ[tr(DN)I−DN]Ω/2+
(3MR²κ²/2)∫s⁴f/(u³N)ds. These are tracer/action references only.

## Проверки и границы

Independent angularintegrals иradialquadrature twolevels; cotangent work,
axialcharge, metric quadraticform иpositivecurrentdensity/Jacobian.
Wrongcontrols: forwardmomentum A p, Euclidean p=mV, position A x,
centre-affineD, densityρ* treated as scalar. Decomposition и3D geometry
не квалифицируют PNtensor/EOS/stress/gravitationalfieldspin/ADMcentre.
Actual bodyconservative Hamiltonian, qualified lunarinitialization иtides
остаются будущими задачами, даже при точном numericalagreement.
