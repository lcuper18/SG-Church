# Generated manually to match tenants/models.py (expanded COUNTRY_CHOICES/CURRENCY_CHOICES)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0005_alter_tenant_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='country',
            field=models.CharField(
                blank=True,
                choices=[
                    ('AR', 'Argentina'), ('BO', 'Bolivia'), ('BR', 'Brasil'),
                    ('CA', 'Canadá'), ('CL', 'Chile'), ('CO', 'Colombia'),
                    ('CR', 'Costa Rica'), ('CU', 'Cuba'), ('EC', 'Ecuador'),
                    ('SV', 'El Salvador'), ('ES', 'España'), ('US', 'Estados Unidos'),
                    ('GQ', 'Guinea Ecuatorial'), ('GT', 'Guatemala'), ('HN', 'Honduras'),
                    ('MX', 'México'), ('NI', 'Nicaragua'), ('PA', 'Panamá'),
                    ('PY', 'Paraguay'), ('PE', 'Perú'), ('PR', 'Puerto Rico'),
                    ('DO', 'República Dominicana'), ('UY', 'Uruguay'), ('VE', 'Venezuela'),
                    ('DE', 'Alemania'), ('AU', 'Australia'), ('ZA', 'Sudáfrica'),
                    ('KR', 'Corea del Sur'), ('CN', 'China'), ('PH', 'Filipinas'),
                    ('FR', 'Francia'), ('IN', 'India'), ('IE', 'Irlanda'),
                    ('IT', 'Italia'), ('JP', 'Japón'), ('KE', 'Kenia'),
                    ('NG', 'Nigeria'), ('NZ', 'Nueva Zelanda'), ('NL', 'Países Bajos'),
                    ('PT', 'Portugal'), ('GB', 'Reino Unido'), ('SG', 'Singapur'),
                    ('SE', 'Suecia'), ('CH', 'Suiza'),
                ],
                help_text='ISO country code',
                max_length=2,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='tenant',
            name='currency',
            field=models.CharField(
                choices=[
                    ('USD', 'Dólar estadounidense'), ('EUR', 'Euro'), ('JPY', 'Yen japonés'),
                    ('GBP', 'Libra esterlina'), ('CNY', 'Yuan chino'), ('AUD', 'Dólar australiano'),
                    ('CAD', 'Dólar canadiense'), ('CHF', 'Franco suizo'), ('HKD', 'Dólar de Hong Kong'),
                    ('SGD', 'Dólar de Singapur'), ('MXN', 'Peso mexicano'), ('COP', 'Peso colombiano'),
                    ('ARS', 'Peso argentino'), ('CLP', 'Peso chileno'), ('PEN', 'Sol peruano'),
                    ('BRL', 'Real brasileño'), ('CRC', 'Colón costarricense'), ('GTQ', 'Quetzal guatemalteco'),
                    ('HNL', 'Lempira hondureño'), ('NIO', 'Córdoba nicaragüense'), ('PAB', 'Balboa panameño'),
                    ('DOP', 'Peso dominicano'), ('UYU', 'Peso uruguayo'), ('BOB', 'Boliviano'),
                    ('PYG', 'Guaraní paraguayo'), ('VES', 'Bolívar venezolano'),
                ],
                default='USD',
                max_length=3,
            ),
        ),
    ]
