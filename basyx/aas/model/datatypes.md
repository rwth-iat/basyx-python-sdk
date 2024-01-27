Missing constants:
- Duration
- DateTime 
- Time
- Boolean
- Double
- Decimal
- Integer
- String

Used constants:
- AnyXSDType, XSD_TYPE_NAMES, XSD_TYPE_CLASSES: similar logic to these constants is implemented in the constants DataTypeDefXSD (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/types.py#L4939) and _DATA_TYPE_DEF_XSD_TO_VALUE_CONSISTENCY (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1451C1-L1451C40)
- DURATION_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L647C1-L647C1)
- DATETIME_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L553)
- TIME_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L847)
- DATE_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L520C4-L520C4)
- GYEAR_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L774)
- GMONTH_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L724)
- GDAY_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L698)
- GYEARMONTH_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L799)
- GMONTHDAY_RE (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L749)


Missing functions:
- trivial_cast
- _serialize_date_tzinfo
- _serialize_duration
- _parse_xsd_duration
- _parse_xsd_date_tzinfo
- _parse_xsd_date
- _parse_xsd_datetime
- _parse_xsd_time
- _parse_xsd_bool
- _parse_xsd_gyear
- _parse_xsd_gmonth
- _parse_xsd_gday
- _parse_xsd_gyearmonth
- _parse_xsd_gmonthday

Used functions: 
- from_xsd. Although it does not deserialize, the function value_consistent_with_xsd_type implements a similar logic (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1491C5-L1491C35). The real deserialization takes place in xmlization.py in the "ReaderandSetter" classes and functions (location example: https://github.com/aas-core-works/aas-core3.0-python/blob/d3a1f793732f6fa30db7674010cfd3f7bc65023d/aas_core3/xmlization.py#L10952)
- xsd_repr (location: https://github.com/aas-core-works/aas-core3.0-python/blob/d3a1f793732f6fa30db7674010cfd3f7bc65023d/aas_core3/xmlization.py#L26484)

Date:
- Does not possess Class Date.
- Similar logic is instead implemented in function is_xs_date (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1264C5-L1264C15)
- Missing constants:
  - `__slots__`
- Missing functions:
  - begin
  - tzinfo (@property)
  - utcoffset
  - `__repr__`
  - `__eq__`

GYearMonth:
- Does not possess Class GYearMonth.
- Similar logic is instead implemented in function matches_xs_g_year_month (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L808)
- Missing constants:
  - `__slots__`
- Missing functions:
  - into_date
  - from_date (@classmethod)
  - `__eq__` 

GYear:
- Does not possess Class GYear.
- Similar logic is instead implemented in function matches_xs_g_year (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L784)
- Missing constants:
  - `__slots__`
- Missing functions:
  - into_date
  - from_date (@classmethod)
  - `__eq__` 

GMonthDay:
- Does not possess Class GMonthDay.
- Similar logic is instead implemented in function is_xs_g_month_day (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1367)
- Missing constants:
  - `__slots__`
- Missing functions:
  - into_date
  - from_date (@classmethod)
  - `__eq__` 

GDay:
- Does not possess Class GDay.
- Similar logic is instead implemented in function matches_xs_g_day (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L708)
- Missing constants:
  - `__slots__`
- Missing functions:
  - into_date
  - from_date (@classmethod)
  - `__eq__` 

GMonth:
- Does not possess Class GMonth.
- Similar logic is instead implemented in function matches_xs_g_month (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L734)
- Missing constants:
  - `__slots__`
- Missing functions:
  - into_date
  - from_date (@classmethod)
  - `__eq__` 

Base64Binary:
- Does not possess Class Base64Binary.
- While we simply `pass`, in aas-core there is a check for Base64Binary. It is implemented in function matches_xs_base_64_binary (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L476)

HexBinary:
- Does not possess Class HexBinary.
- While we simply `pass`, in aas-core there is a check for HexBinary. It is implemented in function matches_xs_hex_binary (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L832)

Float:
- Does not possess Class Float.
- While we simply `pass`, in aas-core there is a check for Float. It is implemented in function is_xs_float (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1333)

Long:
- Does not possess Class Long.
- Similar logic is instead implemented in function is_xs_long (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1379)

Int:
- Does not possess Class Int.
- Similar logic is instead implemented in function is_xs_int (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1388)

Short:
- Does not possess Class Short.
- Similar logic is instead implemented in function is_xs_short (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1397)

Byte:
- Does not possess Class Byte.
- Similar logic is instead implemented in function is_xs_byte (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1406)

NonPositiveInteger:
- Does not possess Class NonPositiveInteger.
- Similar logic is instead implemented in function matches_xs_non_positive_integer (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1144)

NegativeInteger:
- Does not possess Class NegativeInteger.
- Similar logic is instead implemented in function matches_xs_negative_integer (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1168)

NonNegativeInteger:
- Does not possess Class NonNegativeInteger.
- Similar logic is instead implemented in function matches_xs_non_negative_integer (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1000)

PositiveInteger:
- Does not possess Class PositiveInteger.
- Similar logic is instead implemented in function matches_xs_positive_integer (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1024)

UnsignedLong:
- Does not possess Class UnsignedLong.
- Similar logic is instead implemented in function is_xs_unsigned_long (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1415)

UnsignedInt:
- Does not possess Class UnsignedInt.
- Similar logic is instead implemented in function is_xs_unsigned_int (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1424)

UnsignedShort:
- Does not possess Class UnsignedShort.
- Similar logic is instead implemented in function is_xs_unsigned_short (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1433)

UnsignedByte:
- Does not possess Class UnsignedByte.
- Similar logic is instead implemented in function is_xs_unsigned_byte (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L1442)

AnyURI:
- Does not possess Class AnyURI.
- While we simply `pass`, in aas-core there is a check for AnyURI. It is implemented in function matches_xs_any_uri (location: https://github.com/aas-core-works/aas-core3.0-python/blob/2852e168581b76d206f6d1e60f0fe404504a0efd/aas_core3/verification.py#L440)

NormalizedString:
- Does not possess Class NormalizedString.
- Missing functions:
 - from_string (@classmethod)

