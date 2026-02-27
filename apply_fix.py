import os

path = 'apps/orders/serializers.py'
with open(path, 'r') as f:
    content = f.read()

old_logic = """    def validate_custom_styles(self, value):
        \"\"\"Validate custom_styles array structure\"\"\"
        if value is None:
            return None
        
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_styles must be an array")
        
        required_fields = ['style_type', 'index', 'label', 'asset_path']
        
        for idx, style in enumerate(value):
            if not isinstance(style, dict):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}] must be an object"
                )
            
            # Check required fields
            for field in required_fields:
                if field not in style:
                    raise serializers.ValidationError(
                        f"custom_styles[{idx}] is missing required field: {field}"
                    )
            
            # Validate field types
            if not isinstance(style['style_type'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].style_type must be a string"
                )
            
            if not isinstance(style['index'], int):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].index must be an integer"
                )
            
            if not isinstance(style['label'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].label must be a string"
                )
            
            if not isinstance(style['asset_path'], str):
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].asset_path must be a string"
                )
            
            # Validate index is non-negative
            if style['index'] < 0:
                raise serializers.ValidationError(
                    f"custom_styles[{idx}].index must be a non-negative integer"
                )
        
        return value"""

new_logic = """    def validate_custom_styles(self, value):
        \"\"\"Validate custom_styles and enrich ID-only format with full details\"\"\"
        if value is None:
            return None
        
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_styles must be an array")
        
        enriched_styles = []
        for idx, style in enumerate(value):
            if not isinstance(style, dict):
                raise serializers.ValidationError(f"custom_styles[{idx}] must be an object")
            
            # Scenario 1: ID-only format {"style_id": 8, "category": "collar"}
            if 'style_id' in style:
                style_id = style.get('style_id')
                try:
                    style_obj = CustomStyle.objects.select_related('category').get(id=style_id, is_active=True)
                    enriched_styles.append({
                        "style_type": style_obj.category.name,
                        "index": style_obj.display_order,
                        "label": style_obj.name,
                        "asset_path": style_obj.image.name if style_obj.image else ""
                    })
                except CustomStyle.DoesNotExist:
                    raise serializers.ValidationError(f"Custom style with ID {style_id} not found or inactive")
            
            # Scenario 2: Traditional format (for backward compatibility)
            else:
                required_fields = ['style_type', 'index', 'label', 'asset_path']
                for field in required_fields:
                    if field not in style:
                        raise serializers.ValidationError(
                            f"custom_styles[{idx}] must contain either 'style_id' or '{field}'"
                        )
                enriched_styles.append(style)
        
        return enriched_styles"""

# Replace all occurrences
new_content = content.replace(old_logic, new_logic)

if content == new_content:
    print("Warning: Content didn't change! Substring mismatch.")
    # Try more flexible approach
else:
    with open(path, 'w') as f:
        f.write(new_content)
    print("Successfully updated serializers.py")
