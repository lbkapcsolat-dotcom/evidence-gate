import EquilibriumBridgeReproof

open EquilibriumBridgeReproof

#check galois_adjunction
#check phi_monotone
#check L_monotone
#check unit
#check counit
#check unit_naturality
#check counit_naturality
#check fiber_semantic_safety
#check cubical_negative_control
#check relative_pair_cardinalities
#check phi_L_retraction_on_system_image

example : badCubicalCount = 6 := cubical_negative_control
example : phiImageCount = 32 := phi_image_count
example : maxFiberSize = 3 := fiber_semantic_safety
example : systemKCount = 31 := system_K_count
example : systemACount = 30 := system_A_count
example : genomicKCount = 61 := genomic_K_count
example : genomicACount = 60 := genomic_A_count
