"""Small numeric contract extracted from the reviewed converter dependencies."""
from decimal import Decimal, InvalidOperation, localcontext
CHANNELS = 'CMYKWT'
FIELDS = ('cyan', 'magenta', 'yellow', 'black', 'white', 'clear')
class ValidationError(ValueError):
    pass

def validate_recipe(values, *, order='CMYKWT', tolerance=Decimal(0)):
    if len(order) != 6 or set(order) != set(CHANNELS):
        raise ValidationError('Channel order must explicitly contain C M Y K W T exactly once.')
    if not tolerance.is_finite() or tolerance < 0 or tolerance > Decimal('0.1'):
        raise ValidationError('Sum tolerance must be finite and between 0 and 0.1 percentage points.')
    if len(values) != 6:
        raise ValidationError('Exactly six positional channel values are required; missing positions are ambiguous.')
    numbers = []
    for value in values:
        if isinstance(value, bool):
            raise ValidationError('Boolean is not a channel percentage.')
        try:
            d = Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            raise ValidationError(f'Invalid channel percentage: {value!r}')
        if d.is_finite() and (len(d.as_tuple().digits)>64 or abs(d.as_tuple().exponent)>64):
            raise ValidationError('Channel decimal exceeds supported 64-digit/exponent precision limit.')
        if not d.is_finite() or not Decimal(0) <= d <= Decimal(100):
            raise ValidationError(f'Channel percentage outside finite 0..100: {value!r}')
        numbers.append(d)
    with localcontext() as ctx:
        ctx.prec = max(64, sum(len(x.as_tuple().digits) + abs(x.as_tuple().exponent) for x in numbers) + 10)
        total = sum(numbers, Decimal(0))
        difference = abs(total - Decimal(100))
    if difference > tolerance:
        raise ValidationError(f'Channel total is {total}, not 100 (tolerance {tolerance}). No normalization performed.')
    recipe = dict(zip(order, numbers))
    return {'channels': {k: str(recipe[k]) for k in CHANNELS}, 'total': str(total), 'sum_tolerance': str(tolerance)}

