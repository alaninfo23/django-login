from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0004_alter_centrocusto_unique_together_and_more'),
        ('empresa', '0002_empresa_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='centrocusto',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='centros_custo', to='empresa.empresa'),
        ),
        migrations.AlterField(
            model_name='subgrupo',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subgrupos', to='empresa.empresa'),
        ),
        migrations.AlterField(
            model_name='formapagamento',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='formas_pagamento', to='empresa.empresa'),
        ),
        migrations.AlterField(
            model_name='despesa',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='despesas', to='empresa.empresa'),
        ),
        migrations.AlterField(
            model_name='repasse',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repasses', to='empresa.empresa'),
        ),
    ]
