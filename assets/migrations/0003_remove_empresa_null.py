from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0002_asset_empresa_alter_asset_asset_type'),
        ('empresa', '0002_empresa_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assets', to='empresa.empresa'),
        ),
    ]
